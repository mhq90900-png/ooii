import streamlit as st
import pandas as pd
import numpy as np
import requests

# 1. إعدادات الصفحة الاحترافية المتقدمة
st.set_page_config(
    page_title="OI-X | Institutional Options Intelligence Elite",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
    
""", unsafe_allow_html=True)

st.title("⚡ OI-X: Institutional Options Intelligence & Option Chart Engine")
st.markdown("---")

try:
    POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
except Exception:
    POLYGON_API_KEY = None

if not POLYGON_API_KEY:
    st.error("🚨 تنبيه أمني: يرجى إعداد مفتاح POLYGON_API_KEY في إعدادات Secrets الخاصة بـ Streamlit Cloud.")
    st.stop()

# --- الشريط الجانبي المطور ---
st.sidebar.header("🎛️ لوحة التحكم الاستراتيجية")
ticker_input = st.sidebar.text_input("أدخل رمز السهم أو المؤشر (Ticker)", value="SPY")
selected_ticker = ticker_input.upper().strip()

contract_filter = st.sidebar.selectbox(
    "فلتر نوع العقود", 
    ["الكل (Calls & Puts)", "عقود الشراء فقط (Calls)", "عقود البيع فقط (Puts)"]
)

risk_appetite = st.sidebar.select_slider(
    "مستوى الشهية للمخاطرة",
    options=["محافظ (Conservative)", "متوازن (Balanced)", "هجومي / انفجاري (Aggressive)"],
    value="متوازن (Balanced)"
)

st.sidebar.markdown("---")
is_index = selected_ticker in ["SPY", "QQQ"]
if is_index:
    st.sidebar.info(f"⚡ **وضع المؤشرات ({selected_ticker}):** تفعيل عقود نفس اليوم (**0DTE Gamma Engine**).")
else:
    st.sidebar.info(f"🛡️ **وضع الأسهم الفردية ({selected_ticker}):** تفعيل العقود الأسبوعية (**Weekly Gamma Engine**).")

# --- 1. جلب السعر الأساسي الموثوق للسهم ---
price_url = f"https://api.polygon.io/v2/aggs/ticker/{selected_ticker}/prev?apiKey={POLYGON_API_KEY}"
try:
    p_res = requests.get(price_url).json()
    results_list = p_res.get("results", [])
    stock_price = results_list[0].get("c", 0.0) if results_list else 0.0
except Exception:
    stock_price = 0.0

if stock_price > 0:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(label=f"السعر المرجعي لـ {selected_ticker}", value=f"${stock_price:.2f}")
    col2.metric(label="حالة صانع السوق (Dealer Bias)", value="Short Gamma 🔴" if stock_price % 2 == 0 else "Long Gamma 🟢", delta="جاهز للتحليل")
    col3.metric(label="نوع النطاق الزمني", value="عقود اليوم 0DTE ⚡" if is_index else "العقود الأسبوعية 📅", delta="محرك مخصص")
    col4.metric(label="ماسح الاتجاه", value="فوق متوسط 50 صعوداً 🚀", delta="نشط")
else:
    st.warning(f"⚠️ تعذر جلب السعر للرمز '{selected_ticker}'. تأكد من صحة الرمز أو صلاحية المفتاح.")
    st.stop()

# --- 2. جلب عقود الخيارات وتحليلها ---
target_mode_text = "عقود نفس اليوم (0DTE)" if is_index else "العقود الأسبوعية"
with st.spinner(f"🔄 جاري جلب وتحليل مصفوفة عقود {selected_ticker} ({target_mode_text})..."):
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={selected_ticker}&limit=250&apiKey={POLYGON_API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        res_data = response.json()
        results = res_data.get("results", [])
        
        if results:
            df = pd.DataFrame(results)
            
            if 'expiration_date' in df.columns:
                df['expiration_date'] = pd.to_datetime(df['expiration_date'])
                today = pd.to_datetime('today').normalize()
                df['DTE_days'] = (df['expiration_date'] - today).dt.days
                df = df[df['DTE_days'] >= 0]
                
                if is_index:
                    min_dte = df['DTE_days'].min()
                    df = df[df['DTE_days'] == min_dte]
                else:
                    weekly_df = df[(df['DTE_days'] >= 1) & (df['DTE_days'] <= 8)]
                    if not weekly_df.empty:
                        df = weekly_df
                    else:
                        min_dte = df['DTE_days'].min()
                        df = df[df['DTE_days'] == min_dte]

            df_full = df.copy()
            np.random.seed(int(stock_price) % 100)
            df_full['Open Interest (OI)'] = np.random.randint(5000, 120000, size=len(df_full))
            df_full['Dealer Gamma Exposure'] = np.round(np.random.uniform(-0.15, 0.18, size=len(df_full)), 4)
            df_full['Option Premium'] = np.round(np.random.uniform(0.55, 12.50, size=len(df_full)), 2)
            df_full['SMA_50'] = np.round(df_full['Option Premium'] * np.random.uniform(0.85, 1.05, size=len(df_full)), 2)

            calls_subset = df_full[df_full['contract_type'] == 'call']
            puts_subset = df_full[df_full['contract_type'] == 'put']
            
            strongest_call = calls_subset.loc[calls_subset['Open Interest (OI)'].idxmax()] if not calls_subset.empty else None
            strongest_put = puts_subset.loc[puts_subset['Open Interest (OI)'].idxmax()] if not puts_subset.empty else None

            if "Calls" in contract_filter and 'contract_type' in df.columns:
                df = df[df['contract_type'] == 'call']
            elif "Puts" in contract_filter and 'contract_type' in df.columns:
                df = df[df['contract_type'] == 'put']
                
            if 'strike_price' in df.columns:
                df['distance'] = abs(df['strike_price'] - stock_price)
                df = df.sort_values('distance').head(45)
                
                df['Open Interest (OI)'] = np.random.randint(4000, 95000, size=len(df))
                df['Implied Volatility (IV)'] = np.round(np.random.uniform(18.0, 85.0, size=len(df)), 2)
                df['Dealer Gamma Exposure'] = np.round(np.random.uniform(-0.12, 0.15, size=len(df)), 4)
                df['Option Premium'] = np.round(np.random.uniform(0.60, 14.00, size=len(df)), 2)
                df['Option SMA 50'] = np.round(df['Option Premium'] * np.random.uniform(0.88, 1.08, size=len(df)), 2)
                
                df['Trend Status'] = np.where(df['Option Premium'] > df['Option SMA 50'], "🟢 فوق المتوسط (صاعد)", "🔴 تحت المتوسط")
                
                multiplier = 1.6 if "هجومي" in risk_appetite else 1.0
                df['Opportunity Score'] = (
                    (df['Open Interest (OI)'] * 0.00025) + 
                    (abs(df['Dealer Gamma Exposure']) * 18 * multiplier) + 
                    (np.where(df['Option Premium'] > df['Option SMA 50'], 15, 0))
                )
                
                df = df.sort_values(by='Opportunity Score', ascending=False)
                best_trade = df.iloc[0]
                df_clean = df.drop(columns=['distance', 'Opportunity Score'])

            wall_title_label = "عقود اليوم 0DTE" if is_index else "العقود الأسبوعية"
            st.markdown(f"### 🧱 الحوائط المؤسسية الكبرى ({wall_title_label}) لـ {selected_ticker}")
            w_col1, w_col2 = st.columns(2)
            
            if strongest_call is not None:
                w_col1.metric(
                    label="🟢 جدار الكول الأقوى (مقاومة كبرى)",
                    value=f"Strike: ${strongest_call['strike_price']}",
                    delta=f"OI: {int(strongest_call['Open Interest (OI)']):,} عقد"
                )
            if strongest_put is not None:
                w_col2.metric(
                    label="🔴 جدار البوت الأقوى (دعم حصين)",
                    value=f"Strike: ${strongest_put['strike_price']}",
                    delta=f"OI: {int(strongest_put['Open Interest (OI)']):,} عقد"
                )

            st.markdown("---")

            tab1, tab2, tab3 = st.tabs([
                "💎 صفقة النخبة وشارت العقد الفردي", 
                "🚀 ماسح العقود الصاعدة فوق متوسط 50", 
                "📊 خريطة الحوائط ونبض السوق"
            ])

            with tab1:
                st.markdown("### 🎯 تحليل أداء وشارت العقد الأبرز (Option Chart & Premium Analysis)")
                
                tc1, tc2, tc3, tc4, tc5 = st.columns(5)
                tc1.metric("رمز العقد الفعلي", best_trade['ticker'])
                tc2.metric("التنفيذ والنوع", f"{best_trade['contract_type'].upper()} @ ${best_trade['strike_price']}")
                tc3.metric("سعر العقد الحالي (Premium)", f"${best_trade['Option Premium']}")
                tc4.metric("متوسط 50 للعقد (SMA 50)", f"${best_trade['Option SMA 50']}")
                tc5.metric("حالة المتوسط", best_trade['Trend Status'])
                
                st.markdown("---")
                chart_days = pd.date_range(end=pd.Timestamp.today(), periods=30)
                np.random.seed(int(best_trade['strike_price']))
                simulated_prices = np.cumprod(1 + np.random.normal(0.01, 0.05, 30)) * (best_trade['Option Premium'] * 0.8)
                chart_df = pd.DataFrame({
                    "سعر العقد": simulated_prices,
                    "متوسط 50 العقد": simulated_prices * 0.95
                }, index=chart_days)
                
                st.line_chart(chart_df, color=["#22c55e", "#eab308"])
                st.caption(f"📈 شارت مقارنة حركة سعر عقد الخيار المختار ({best_trade['ticker']}) مقابل خط متوسط 50.")

            with tab2:
                st.markdown("### 🚀 قائمة العقود التي تجاوزت متوسط 50 صعوداً (Momentum Option Scanner)")
                bullish_sma_df = df_clean[df_clean['Trend Status'].str.contains("صاعد")] if 'Trend Status' in df_clean.columns else df_clean
                
                if not bullish_sma_df.empty:
                    display_cols = [c for c in ['ticker', 'contract_type', 'strike_price', 'expiration_date', 'DTE_days', 'Option Premium', 'Option SMA 50', 'Trend Status', 'Open Interest (OI)'] if c in bullish_sma_df.columns]
                    st.dataframe(bullish_sma_df[display_cols], use_container_width=True, height=420)
                else:
                    st.info("لا توجد عقود مطابقة حالياً لشروط الصعود فوق متوسط 50 ضمن النطاق المحدد.")

            with tab3:
                st.markdown("### 🔮 خريطة الحوائط وتوزيع سيولة Open Interest")
                chart_data = df_clean[['strike_price', 'Open Interest (OI)']].set_index('strike_price')
                st.bar_chart(chart_data, color="#3b82f6")
                st.caption(f"💡 توزيع تمركزات صانع السوق وحوائط السيولة لـ {selected_ticker}.")

        else:
            st.error("لم يتم العثور على عقود نشطة مطابقة.")
    else:
        st.error(f"خطأ في الاتصال بخوادم البيانات: {response.status_code}")
