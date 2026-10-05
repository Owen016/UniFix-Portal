import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import time
from datetime import datetime

# ==========================================
# 1. DATABASE & CONFIGURATION
# ==========================================
ALLOWED_DOMAIN = "@owen.ac.th"  # โดเมนอีเมลสถาบันที่อนุญาต

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    # ตารางเก็บผู้ใช้งาน
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            fullname TEXT NOT NULL,
            role TEXT DEFAULT 'Student'
        )
    """)
    # ตารางเก็บข้อมูลการแจ้งปัญหา
    c.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            category TEXT,
            location TEXT,
            title TEXT,
            description TEXT,
            department TEXT,
            status TEXT DEFAULT '⏳ รอรับเรื่อง',
            created_at TEXT,
            FOREIGN KEY (user_email) REFERENCES users (email)
        )
    """)
    conn.commit()
    conn.close()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def add_user(email, password, fullname):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (email, password, fullname) VALUES (?,?,?)", 
                  (email, make_hashes(password), fullname))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(email, password):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email,))
    data = c.fetchone()
    conn.close()
    if data and check_hashes(password, data[1]):
        return data
    return None

def add_ticket(email, category, location, title, description, department):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute("""
        INSERT INTO tickets (user_email, category, location, title, description, department, created_at)
        VALUES (?,?,?,?,?,?,?)
    """, (email, category, location, title, description, department, now))
    conn.commit()
    conn.close()

def get_user_tickets(email):
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT id, category, location, title, description, department, status, created_at FROM tickets WHERE user_email = ? ORDER BY id DESC", conn, params=(email,))
    conn.close()
    return df

def get_all_tickets():
    conn = sqlite3.connect("database.db")
    df = pd.read_sql_query("SELECT id, user_email, category, location, title, description, department, status, created_at FROM tickets ORDER BY id DESC", conn)
    conn.close()
    return df

def update_ticket_status(ticket_id, new_status):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE tickets SET status = ? WHERE id = ?", (new_status, ticket_id))
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. PAGE CONFIG & CUSTOM MODERN CSS
# ==========================================
st.set_page_config(page_title="Campus Helpdesk & Reporting System", page_icon="🛠️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Kanit', sans-serif;
    }
    .main {
        background-color: #f8fafc;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border-radius: 12px;
        padding: 18px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

# Session States
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "download_complete" not in st.session_state:
    st.session_state.download_complete = False

# ==========================================
# 3. AUTHENTICATION (SIGN UP & LOGIN)
# ==========================================
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center; color: #0f172a; font-weight: 600;'>🛠️ Campus Issue Reporting System</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #64748b;'>ระบบแจ้งปัญหาอุปกรณ์และอาคารสถานที่ภายในมหาวิทยาลัย (เฉพาะโดเมน {ALLOWED_DOMAIN})</p>", unsafe_allow_html=True)
    
    st.write("")
    _, col_auth, _ = st.columns([1, 1.2, 1])
    
    with col_auth:
        tabs = st.tabs(["🔑 เข้าสู่ระบบ (Login)", "📝 สมัครสมาชิก (Sign Up)"])
        
        with tabs[0]:
            st.write("")
            email_login = st.text_input("อีเมลสถาบัน", key="login_email", placeholder=f"student{ALLOWED_DOMAIN}")
            pass_login = st.text_input("รหัสผ่าน", type="password", key="login_pass")
            
            if st.button("🚀 เข้าสู่ระบบ", type="primary", use_container_width=True):
                user = login_user(email_login, pass_login)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_email = user[0]
                    st.session_state.user_name = user[2]
                    st.session_state.download_complete = False
                    st.rerun()
                else:
                    st.error("❌ อีเมลหรือรหัสผ่านไม่ถูกต้อง")

        with tabs[1]:
            st.write("")
            st.info(f"🔒 อนุญาตเฉพาะอีเมลที่ลงท้ายด้วย **{ALLOWED_DOMAIN}** เท่านั้น")
            fullname = st.text_input("ชื่อ-นามสกุล", key="signup_name")
            email_signup = st.text_input("อีเมลสถาบัน", key="signup_email", placeholder=f"yourname{ALLOWED_DOMAIN}")
            pass_signup = st.text_input("รหัสผ่าน", type="password", key="signup_pass")
            confirm_pass = st.text_input("ยืนยันรหัสผ่าน", type="password", key="signup_confirm")
            
            if st.button("✨ ลงทะเบียนสมาชิก", type="primary", use_container_width=True):
                if not email_signup.endswith(ALLOWED_DOMAIN):
                    st.error(f"❌ อีเมลต้องลงท้ายด้วย '{ALLOWED_DOMAIN}' เท่านั้น")
                elif pass_signup != confirm_pass:
                    st.error("❌ รหัสผ่านไม่ตรงกัน")
                elif not fullname or not pass_signup:
                    st.error("❌ กรุณากรอกข้อมูลให้ครบถ้วน")
                else:
                    if add_user(email_signup, pass_signup, fullname):
                        st.success("🎉 สมัครสมาชิกสำเร็จ! กรุณาสลับไปหน้า 'เข้าสู่ระบบ'")
                    else:
                        st.error("❌ อีเมลนี้เคยลงทะเบียนไว้แล้ว")

# ==========================================
# 4. PRE-LOADER
# ==========================================
elif st.session_state.logged_in and not st.session_state.download_complete:
    st.markdown("<br><br><h2 style='text-align: center;'>📥 กำลังเชื่อมต่อระบบศูนย์รับเรื่องและฐานข้อมูล...</h2>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #64748b;'>ยินดีต้อนรับคุณ **{st.session_state.user_name}** สู่ระบบแจ้งซ่อมและปัญหา</p>", unsafe_allow_html=True)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(1, 101):
        time.sleep(0.01)
        progress_bar.progress(i)
        if i < 35:
            status_text.text(f"⏳ ตรวจสอบสิทธิ์ผู้ใช้งานสถาบัน... ({i}%)")
        elif i < 75:
            status_text.text(f"📦 ดึงข้อมูลตารางแจ้งซ่อมและฝ่ายที่เกี่ยวข้อง... ({i}%)")
        else:
            status_text.text(f"⚡ จัดเตรียมหน้าจอแสดงผล... ({i}%)")
            
    st.session_state.download_complete = True
    st.rerun()

# ==========================================
# 5. MAIN APPLICATION
# ==========================================
else:
    # Sidebar
    st.sidebar.markdown("## 🛠️ Campus Helpdesk")
    st.sidebar.markdown(f"👤 **{st.session_state.user_name}**")
    st.sidebar.caption(f"📧 {st.session_state.user_email}")
    st.sidebar.divider()
    
    menu = st.sidebar.radio(
        "เมนูหลัก",
        ["🏠 Dashboard สรุปภาพรวม", "📝 แจ้งปัญหาใหม่", "📋 ติดตามสถานะ (ของฉัน)", "⚙️ จัดการปัญหา (สำหรับเจ้าหน้าที่)"]
    )
    
    st.sidebar.divider()
    if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.download_complete = False
        st.session_state.user_email = ""
        st.session_state.user_name = ""
        st.rerun()

    # --- MENU 1: DASHBOARD ---
    if menu == "🏠 Dashboard สรุปภาพรวม":
        st.title("🏠 Dashboard สรุปการแจ้งปัญหาภาพรวม")
        
        all_tickets = get_all_tickets()
        user_tickets = get_user_tickets(st.session_state.user_email)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("เรื่องที่แจ้งทั้งหมดในระบบ", f"{len(all_tickets)} เรื่อง")
        c2.metric("เรื่องที่คุณแจ้งไว้", f"{len(user_tickets)} เรื่อง")
        
        pending_count = len(all_tickets[all_tickets['status'] == '⏳ รอรับเรื่อง']) if not all_tickets.empty else 0
        done_count = len(all_tickets[all_tickets['status'] == '✅ แก้ไขเรียบร้อย']) if not all_tickets.empty else 0
        
        c3.metric("กำลังรอรับเรื่อง", f"{pending_count} เรื่อง")
        c4.metric("แก้ไขเรียบร้อยแล้ว", f"{done_count} เรื่อง")
        
        st.divider()
        col_left, col_right = st.columns([1.2, 1])
        
        with col_left:
            st.subheader("📢 รายการแจ้งปัญหาร่าสุดในมหาลัย")
            if not all_tickets.empty:
                st.dataframe(all_tickets[["id", "category", "location", "title", "department", "status", "created_at"]], use_container_width=True)
            else:
                st.info("ยังไม่มีการแจ้งปัญหาในระบบ")
                
        with col_right:
            st.subheader("💡 คำแนะนำการใช้งาน")
            st.write("1. หากพบเครื่องปรับอากาศเสีย, ไฟฟ้าดับ, หรือโปรเจกเตอร์ไม่ติด สามารถส่งเรื่องในเมนู **'แจ้งปัญหาใหม่'**")
            st.write("2. ระบบจะส่งเรื่องตรงไปยัง **ฝ่ายอาคาร/ไอที/ยานพาหนะ** โดยตรง")
            st.write("3. ผู้แจ้งสามารถติดตามความคืบหน้าสถานะการซ่อมได้แบบ Real-time")

    # --- MENU 2: CREATE NEW TICKET ---
    elif menu == "📝 แจ้งปัญหาใหม่":
        st.title("📝 แบบฟอร์มแจ้งปัญหา / แจ้งซ่อม")
        st.caption("กรุณากรอกรายละเอียดปัญหาให้ชัดเจน เพื่อให้เจ้าหน้าที่เข้าแก้ไขได้รวดเร็ว")
        
        with st.form("ticket_form"):
            col_a, col_b = st.columns(2)
            
            with col_a:
                category = st.selectbox("ประเภทปัญหา*", [
                    "💻 ไอที / อินเทอร์เน็ต / โปรเจกเตอร์",
                    "💡 ไฟฟ้า / เครื่องปรับอากาศ",
                    "🪑 ครุภัณฑ์ / โต๊ะ / เก้าอี้ ชำรุด",
                    "🚪 อาคารสถานที่ / ห้องน้ำ / ความสะอาด",
                    "🚗 ลานจอดรถ / ยานพาหนะ",
                    "❓ อื่นๆ"
                ])
                location = st.text_input("สถานที่เกิดปัญหา (ระบุตึก/ห้อง)*", placeholder="เช่น ตึก 3 ชั้น 4 ห้อง 304")
                
            with col_b:
                department = st.selectbox("ส่งเรื่องถึงหน่วยงาน*", [
                    "ฝ่ายเทคโนโลยีสารสนเทศ (IT)",
                    "ฝ่ายซ่อมบำรุงและอาคารสถานที่",
                    "ฝ่ายยานพาหนะและความปลอดภัย",
                    "ฝ่ายบริหารงานทั่วไป"
                ])
                title = st.text_input("หัวข้อปัญหา (สรุปสั้นๆ)*", placeholder="เช่น แอร์ห้อง 304 น้ำหยดและไม่เย็น")
                
            description = st.text_area("รายละเอียดเพิ่มเติม", placeholder="ระบุอาการเพิ่มเติม เช่น มีเสียงดังผิดปกติ...")
            
            submitted = st.form_submit_button("🚀 ส่งรายงานปัญหา", type="primary", use_container_width=True)
            if submitted:
                if location and title:
                    add_ticket(st.session_state.user_email, category, location, title, description, department)
                    st.success("🎉 ส่งรายงานปัญหาเรียบร้อยแล้ว! เจ้าหน้าที่จะได้รับข้อมูลทันที")
                    st.balloons()
                else:
                    st.error("❌ กรุณากรอกสถานที่และหัวข้อปัญหาให้ครบถ้วน")

    # --- MENU 3: MY TICKETS ---
    elif menu == "📋 ติดตามสถานะ (ของฉัน)":
        st.title("📋 รายการปัญหาที่คุณเคยแจ้งไว้")
        
        user_tickets = get_user_tickets(st.session_state.user_email)
        
        if not user_tickets.empty:
            st.dataframe(user_tickets, use_container_width=True)
        else:
            st.info("คุณยังไม่เคยส่งรายงานปัญหาเข้ามาในระบบ")

    # --- MENU 4: ADMIN / STAFF MANAGEMENT ---
    elif menu == "⚙️ จัดการปัญหา (สำหรับเจ้าหน้าที่)":
        st.title("⚙️ ศูนย์รับเรื่องและเปลี่ยนสถานะ (ฝ่ายซ่อมบำรุง/เจ้าหน้าที่)")
        st.caption("เมนูนี้สำหรับเจ้าหน้าที่เข้ามารับเรื่องและอัปเดตสถานะการแก้ไข")
        
        all_tickets = get_all_tickets()
        
        if not all_tickets.empty:
            st.dataframe(all_tickets, use_container_width=True)
            
            st.divider()
            st.subheader("🔄 อัปเดตสถานะการซ่อม")
            
            col_sel, col_stat, col_btn = st.columns([1, 1, 1])
            
            with col_sel:
                ticket_id = st.selectbox("เลือกหมายเลข Ticket ID:", all_tickets["id"].tolist())
            with col_stat:
                new_status = st.selectbox("สถานะใหม่:", [
                    "⏳ รอรับเรื่อง",
                    "🛠️ กำลังดำเนินการซ่อม",
                    "✅ แก้ไขเรียบร้อย",
                    "❌ ยกเลิก / ข้อมูลไม่ถูกต้อง"
                ])
            with col_btn:
                st.write("")
                st.write("")
                if st.button("💾 บันทึกการเปลี่ยนสถานะ", type="primary", use_container_width=True):
                    update_ticket_status(ticket_id, new_status)
                    st.success(f"อัปเดต Ticket ID #{ticket_id} เป็น '{new_status}' เรียบร้อย!")
                    st.rerun()
        else:
            st.info("ไม่มีรายการแจ้งปัญหาในระบบ")