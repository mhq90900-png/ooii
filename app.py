import streamlit as st
import pandas as pd
import numpy as np
import requests
import math
import plotly.graph_objects as go

# 1. إعدادات الصفحة الاحترافية المتقدمة
st.set_page_config(
    page_title="OI-X | Institutional Options Intelligence Elite",
    page_icon="⚡",
    layout="wide"
)

# تصميم بصري مخصص متطور (Elite Dark Theme CSS)
st.markdown("""
    
""", unsafe_allow_html=True)

st.title("⚡ OI-X: Institutional Options Intelligence & Gamma Engine")
st.markdown("---")

try:
    POLYGON_API_KEY = st.secrets["POLYGON_API_KEY"]
except Exception:
    POLYGON_API_KEY = None

if not POLYGON_API_KEY:
    st.error("🚨 تنبيه أمني: يرجى إعداد مفتاح POLYGON_API_KEY في إعدادات Secrets الخاصة بـ Streamlit Cloud.")
    st.stop()

# --- دالة حساب Gamma التقريبية بأسلوب Black-Scholes ---
def calculate_d1(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0
    return (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))

def calculate_gamma(S, K, T, r, sigma):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0
    d1 = calculate_d1(S, K, T, r, sigma)
    pdf = (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)
    return pdf / (S * sigma * math.sqrt(T))

# --- الشريط الجانبي المطور ---
st.sidebar.header("🎛️ لوحة التحكم الاستراتيجية")
ticker_input = st.sidebar.text_input("أدخل رمز السهم (Ticker)", value="NVDA")
selected_ticker = ticker_input.upper().strip()

contract_filter = st.sidebar.selectbox(
    "فلتر نوع العقود", 
    ["الكل (Calls & Puts)", "عقود الشراء فقط (Calls)", "عقود البيع فقط (Puts)"]
)

# --- إضافة فلتر مدة الانتهاء (0DTE) ---
dte_filter = st.sidebar.radio(
    "⏳ نطاق تاريخ الاستحقاق (DTE Filter)",
    ["جميع العقود المتاحة", "عقود اليوم فقط (0DTE Focus) ⚡", "عقود طويلة الأجل (> 7 أيام) 🛡️"]
)

risk_appetite = st.sidebar.select_slider(
    "مستوى الشهية للمخاطرة",
    options=["محافظ (Conservative)", "متوازن (Balanced)", "هجومي / انفجاري (Aggressive)"],
    value="متوازن (Balanced)"
)

st.sidebar.markdown("---")
st.sidebar.info("💡 **OI-X Engine:** ربط مباشر بين تدفقات صانع السوق (Dealers) ومستويات السيولة الحية.")

# --- 1. جلب السعر الفعلي للسهم ---
price_url = f"https://api.polygon.io/v2/aggs/ticker/{selected_ticker}/prev?apiKey={POLYGON_API_KEY}"
try:
    p_res = requests.get(price_url).json()
    results_list = p_res.get("results", [])
    stock_price = results_list[0].get("c", 0.0) if results_list else 0.0
except Exception:
    stock_price = 0.0

if stock_price <= 0:
    st.warning(f"⚠️ تعذر جلب السعر الفوري للرمز '{selected_ticker}'. تحقق من صحة الرمز ومفتاح API.")
    st.stop()

# --- 2. جلب عقود الخيارات الحية وسلسلة البيانات ---
@st.cache_data(ttl=300)
def fetch_options_chain(ticker, api_key):
    url = f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={ticker}&active=true&limit=1000&apiKey={api_key}"
    res = requests.get(url).json()
    results = res.get("results", [])
    if not results:
        return pd.DataFrame()
    return pd.DataFrame(results)

with st.spinner(f"🔄 جاري تحليل مصفوفة خيارات {selected_ticker} ورسم خارطة GEX..."):
    df_raw = fetch_options_chain(selected_ticker, POLYGON_API_KEY)
    
    if not df_raw.empty and 'strike_price' in df_raw.columns:
        df = df_raw.copy()
        
        # حساب أعداد الأيام للانتهاء DTE
        if 'expiration_date' in df.columns:
            df['expiration_date'] = pd.to_datetime(df['expiration_date'])
            today = pd.to_datetime('today').normalize()
            df['DTE_days'] = (df['expiration_date'] - today).dt.days
            df['DTE'] = df['DTE_days'].apply(lambda x: max(x, 0.5) / 365.0)
        else:
            df['DTE_days'] = 30
            df['DTE'] = 30 / 365.0

        # تطبيق فلتر DTE
        if "0DTE" in dte_filter:
            df = df[df['DTE_days'] <= 1].copy()
        elif "> 7 أيام" in dte_filter:
            df = df[df['DTE_days'] > 7].copy()

        if df.empty:
            st.error("⚠️ لا توجد عقود مطابقة لفلتر تاريخ الانتهاء المحدد.")
            st.stop()

        # تصفية العقود القريبة من السعر الحالي (±25%)
        df = df[(df['strike_price'] >= stock_price * 0.75) & (df['strike_price'] <= stock_price * 1.25)].copy()
        
        df['Open Interest (OI)'] = df.get('open_interest', 1200)
        df['Implied Volatility (IV)'] = 0.45

        # حساب Dealer Gamma Exposure (GEX)
        gex_list = []
        for _, row in df.iterrows():
            gamma_val = calculate_gamma(
                S=stock_price, 
                K=row['strike_price'], 
                T=row['DTE'], 
                r=0.04, 
                sigma=row['Implied Volatility (IV)']
            )
            multiplier = 1 if row.get('contract_type') == 'call' else -1
            gex = (gamma_val * row['Open Interest (OI)'] * 100 * stock_price) / 1e6
            gex_list.append(round(gex * multiplier, 4))

        df['Dealer Gamma Exposure ($M)'] = gex_list

        # استخراج الجدران الرئيسية
        calls_subset = df[df['contract_type'] == 'call']
        puts_subset = df[df['contract_type'] == 'put']
        
        strongest_call = calls_subset.loc[calls_subset['Open Interest (OI)'].idxmax()] if not calls_subset.empty else None
        strongest_put = puts_subset.loc[puts_subset['Open Interest (OI)'].idxmax()] if not puts_subset.empty else None

        total_gex = df['Dealer Gamma Exposure ($M)'].sum()
        
        # حساب نقطة Gamma Flip Level التقريبية
        strikes_gex = df.groupby('strike_price')['Dealer Gamma Exposure ($M)'].sum().reset_index()
        strikes_gex['cum_gex'] = strikes_gex['Dealer Gamma Exposure ($M)'].cumsum()
        flip_row = strikes_gex.iloc[(strikes_gex['cum_gex']).abs().argsort()[:1]]
        gamma_flip_level = flip_row['strike_price'].values[0] if not flip_row.empty else stock_price

        # عرض المؤشرات العلوية
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(label=f"السعر الأساسي لـ {selected_ticker}", value=f"${stock_price:.2f}")
        col2.metric(
            label="حالة صانع السوق (Dealer Bias)", 
            value="Short Gamma 🔴" if total_gex < 0 else "Long Gamma 🟢", 
            delta=f"صافي GEX: ${total_gex:.2f}M"
        )
        col3.metric(label="مستوى انقسام القاما (Gamma Flip)", value=f"${gamma_flip_level:.2f}", delta="نقطة التحول")
        col4.metric(
            label="حالة النظام السعري", 
            value="0DTE High Volatility ⚡" if "0DTE" in dte_filter else ("Gamma Squeeze ⚡" if total_gex < 0 else "Range Pinned 🛡️")
        )

        st.markdown("---")

        # --- عرض أقوى جدار كول وأقوى جدار بوت ---
        st.markdown("### 🧱 الحوائط المؤسسية الكبرى المسيطرة على السوق (Strongest Walls)")
        w_col1, w_col2 = st.columns(2)
        
        if strongest_call is not None:
            w_col1.metric(
                label="🟢 جدار الكول الأقوى (Strongest Call Wall / مقاومة كبرى)",
                value=f"Strike: ${strongest_call['strike_price']}",
                delta=f"OI: {int(strongest_call['Open Interest (OI)']):,} عقد"
            )
        if strongest_put is not None:
            w_col2.metric(
                label="🔴 جدار البوت الأقوى (Strongest Put Wall / دعم حصين)",
                value=f"Strike: ${strongest_put['strike_price']}",
                delta=f"OI: {int(strongest_put['Open Interest (OI)']):,} عقد"
            )

        st.markdown("---")

        # الفلترة للعرض في الجدول
        if "Calls" in contract_filter:
            df_display = df[df['contract_type'] == 'call'].copy()
        elif "Puts" in contract_filter:
            df_display = df[df['contract_type'] == 'put'].copy()
        else:
            df_display = df.copy()

        df_display['distance'] = abs(df_display['strike_price'] - stock_price)
        df_display = df_display.sort_values('distance').head(45)

        # --- نظام التبويبات (Advanced UI Tabs) ---
        tab1, tab2, tab3 = st.tabs([
            "📊 خريطة الحوائط والقاما التفاعلية (Plotly Interactive GEX)", 
            "💎 توصية النخبة والمصفوفة الحية", 
            "🧠 التحليل المؤسسي ونبض الجلسة"
        ])

        with tab1:
            st.markdown("### 📈 خريطة تعرّض القاما التفاعلية (Institutional Gamma & Wall Profile)")
            
            grouped_gex = df.groupby(['strike_price', 'contract_type'])['Dealer Gamma Exposure ($M)'].sum().unstack(fill_value=0).reset_index()
            
            fig = go.Figure()
            
            if 'put' in grouped_gex.columns:
                fig.add_trace(go.Bar(
                    x=grouped_gex['strike_price'],
                    y=grouped_gex['put'],
                    name='Put Gamma (Support)',
                    marker_color='#ef4444'
                ))

            if 'call' in grouped_gex.columns:
                fig.add_trace(go.Bar(
                    x=grouped_gex['strike_price'],
                    y=grouped_gex['call'],
                    name='Call Gamma (Resistance)',
                    marker_color='#22c55e'
                ))

            fig.add_vline(
                x=stock_price, 
                line_dash="dash", 
                line_color="#3b82f6", 
                line_width=3,
                annotation_text=f"السعر الحالي: ${stock_price:.2f}", 
                annotation_position="top right"
            )

            fig.add_vline(
                x=gamma_flip_level, 
                line_dash="dot", 
                line_color="#f59e0b", 
                line_width=2,
                annotation_text=f"Flip Level: ${gamma_flip_level:.2f}", 
                annotation_position="bottom left"
            )

            fig.update_layout(
                title=f"توزيع تعرّض القاما (GEX) لـ {selected_ticker} حسب سعر التنفيذ",
                xaxis_title="سعر التنفيذ (Strike Price)",
                yaxis_title="Dealer GEX ($ Millions)",
                barmode='relative',
                paper_bgcolor='#0b0f19',
                plot_bgcolor='#131b2e',
                font=dict(color='#cbd5e1'),
                height=520,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )

            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.markdown("### 🎯 المصفوفة الحية لفرص العقود")
            cols_to_show = ['ticker', 'contract_type', 'strike_price', 'expiration_date', 'DTE_days', 'Open Interest (OI)', 'Dealer Gamma Exposure ($M)']
            valid_cols = [c for c in cols_to_show if c in df_display.columns]
            st.dataframe(df_display[valid_cols], use_container_width=True, height=420)

        with tab3:
            st.markdown("### 🔮 مؤشر نبض السوق والتوقعات الهيكلية")
            st.info(f"**نقطة التحول الحرج (Gamma Flip Level):** عند سعر **${gamma_flip_level:.2f}**. تداول السهم أعلى هذا المستوى يعني الدخول في **Long Gamma Zone** (استقرار السعر)، بينما التداول أدناه يدخل السهم في **Short Gamma Zone** (انفجار وتسرّع في الحركة).")

    else:
        st.error(f"لم يتم العثور على عقود خيارات نشطة لـ {selected_ticker}.")
