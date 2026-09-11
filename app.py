import streamlit as st
import pandas as pd
import requests

# إعدادات الصفحة الاحترافية
st.set_page_config(
    page_title="OI-X Options Intelligence Platform",
    layout="wide"
)

st.title("⚡ OI-X: US Options Intelligence & Dealer Positioning")
st.markdown("---")

# جلب مفتاح الأمان بأمان من إعدادات Streamlit Secrets
try:
    POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
except Exception:
    POLYGON_API_KEY = None

# التحقق من وجود المفتاح
if not POLYGON_API_KEY:
    st.warning("⚠️ يرجى إعداد مفتاح POLYGON_API_KEY في إعدادات Secrets على منصة Streamlit Cloud لتمكين البيانات الحية.")
    demo_mode = True
else:
    demo_mode = False

# شريط جانبي للتحكم بالمؤشرات والرموز
st.sidebar.header("🎛️ أدوات التحكم والفلترة")
selected_ticker = st.sidebar.selectbox("اختر رمز الأسهم (Ticker)", ["AVGO", "NVDA", "TSLA", "SPY", "QQQ"])
analysis_mode = st.sidebar.radio("نوع التحليل", ["Dealer Gamma Positioning", "Open Interest Volume Flow"])

st.subheader(f"📊 تحليل هيكل الخيارات للرمز: {selected_ticker}")

if demo_mode:
    data = {
        "Ticker": [selected_ticker, selected_ticker, selected_ticker],
        "Option Type": ["CALL", "PUT", "CALL"],
        "Strike Price": [190.0, 120.0, 250.0],
        "Open Interest": [14500, 8200, 12900],
        "Volume": [3400, 1500, 2800],
        "Signal Quality": ["🔥 Bullish Flow", "🛡️ Support Wall", "🔥 Bullish Flow"]
    }
    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True)
    st.info("💡 ملاحظة: هذه بيانات تجريبية (Demo) وسيتم ربطها بالتدفق الحقيقي لـ Polygon بمجرد إضافة المفتاح في Secrets.")
else:
    with st.spinner(f"جاري جلب بيانات السوق الحية لـ {selected_ticker} من Polygon..."):
        try:
            url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={selected_ticker}&limit=10&apiKey={POLYGON_API_KEY}"
            response = requests.get(url)
            if response.status_code == 200:
                res_data = response.json()
                results = res_data.get("results", [])
                if results:
                    live_df = pd.DataFrame(results)
                    st.success("تم الاتصال بـ Polygon.io بنجاح وجلب العقود النشطة!")
                    st.dataframe(live_df[['ticker', 'contract_type', 'strike_price', 'expiration_date']], use_container_width=True)
                else:
                    st.error("لم يتم العثور على عقود نشطة لهذا الرمز حالياً.")
            else:
                st.error(f"خطأ في الاتصال بالخادم: {response.status_code}")
        except Exception as e:
            st.error(f"حدث خطأ أثناء الاتصال بالمنصة:) {e}")
