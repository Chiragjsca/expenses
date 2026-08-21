"""
Expense Tracker — Streamlit App
------------------------------------------------
A single-file Streamlit budgeting app:
  - Home screen: donut chart of spending by category, category grid,
    balance bar, EXPENSE / INCOME buttons
  - New expense / New income: Windows-Calculator-style keypad + account
    + category + note
  - New transfer: move money between accounts
  - Accounts drawer: manage accounts, see balances
  - Categories drawer: manage expense & income categories
  - Filter drawer: Day / Week / Month / Year / All / Interval / Choose date

Run with:  streamlit run monefy_clone.py
"""

import re
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# ────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + THEME
# ────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="centered")

GREEN = "#6FBF8B"
GREEN_DARK = "#5CAE7A"
RED = "#E27272"
BG = "#EAF7EE"
CALC_BG = "#F3F3F3"
CALC_BORDER = "#E1E1E1"
CALC_BLUE = "#0067C0"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    div.block-container {{ padding-top: 1rem; max-width: 480px; }}
    .app-header {{
        background-color: {GREEN}; color: white; padding: 14px 18px;
        border-radius: 8px; font-size: 22px; font-weight: 600;
        display:flex; justify-content:space-between; align-items:center;
        margin-bottom: 6px;
    }}
    .app-sub {{ font-size:13px; opacity:0.9; font-weight:400; }}
    .balance-bar {{
        background-color:{GREEN}; color:white; text-align:center;
        padding:14px; border-radius:6px; font-size:18px; font-weight:600;
        margin: 14px 0;
    }}
    div.stButton > button {{
        border-radius: 6px; border: 1px solid {GREEN}; color:{GREEN_DARK};
        background-color: white;
    }}
    div.stButton > button:hover {{ border-color:{GREEN_DARK}; color:white; background-color:{GREEN}; }}
    .expense-btn button {{ border-color:{RED} !important; color:{RED} !important; }}
    .income-btn button {{ border-color:{GREEN} !important; color:{GREEN_DARK} !important; }}

    /* ---- Windows-Calculator-style keypad ---- */
    .calc-wrap {{
        background-color:{CALC_BG}; border:1px solid {CALC_BORDER};
        border-radius:8px; padding:14px 14px 4px 14px; margin-bottom:10px;
    }}
    .calc-title {{ font-size:20px; font-weight:600; color:#1B1B1B; margin-bottom:6px; }}
    .calc-display {{
        text-align:right; font-size:44px; font-weight:400; color:#1B1B1B;
        padding: 10px 4px 4px 4px; min-height:56px; word-break:break-all;
    }}
    .calc-memrow {{
        display:flex; justify-content:space-between; color:#B0B0B0;
        font-size:14px; padding: 6px 2px 10px 2px; border-bottom:1px solid {CALC_BORDER};
        margin-bottom:8px;
    }}
    .calc-wrap div.stButton > button {{
        width:100%; height:52px; border-radius:6px; border:none;
        background-color:#FFFFFF; color:#1B1B1B; font-size:17px;
        box-shadow: 0 0 0 1px {CALC_BORDER} inset;
    }}
    .calc-wrap div.stButton > button:hover {{
        background-color:#E9E9E9; color:#1B1B1B; box-shadow:0 0 0 1px {CALC_BORDER} inset;
    }}
    .calc-eq div.stButton > button {{
        background-color:{CALC_BLUE} !important; color:white !important;
    }}
    .calc-eq div.stButton > button:hover {{ background-color:#00559C !important; }}
</style>
""", unsafe_allow_html=True)

# ────────────────────────────────────────────────────────────────────────
# SESSION STATE / DATA MODEL
# ────────────────────────────────────────────────────────────────────────
def init_state():
    ss = st.session_state
    ss.setdefault("accounts", {
        "Cash": {"icon": "💵", "balance": 0.0},
        "Payment card": {"icon": "💳", "balance": 0.0},
    })
    ss.setdefault("expense_categories", {
        "Food": "🛒", "Car": "🚗", "Transport": "🚆", "Entertainment": "🍸",
        "House": "🏠", "Taxi": "🚕", "Eating out": "🍴", "Clothes": "👕",
        "Toiletry": "🧴", "Gifts": "🎁", "Sports": "🏃", "Health": "🌡️",
        "Communications": "📞", "Pets": "🐈", "Bills": "🏷️",
    })
    ss.setdefault("income_categories", {
        "Deposits": "💰", "Salary": "🪙", "Savings": "🐷",
    })
    ss.setdefault("transactions", [])  # list of dicts
    ss.setdefault("page", "home")
    ss.setdefault("period", "Month")
    ss.setdefault("calc_buffer", "0")
    ss.setdefault("preset_category", None)
    ss.setdefault("preset_kind", None)

init_state()

def fmt(v):
    return f"₹{v:,.2f}"

def navigate(page, **preset):
    st.session_state.page = page
    st.session_state.preset_category = preset.get("category")
    st.session_state.preset_kind = preset.get("kind")
    st.rerun()

# ────────────────────────────────────────────────────────────────────────
# FILTERING
# ────────────────────────────────────────────────────────────────────────
def period_bounds(period, anchor=None, custom=None):
    today = anchor or date.today()
    if period == "Day":
        return today, today, today.strftime("%A, %d %B")
    if period == "Week":
        start = today - timedelta(days=today.weekday() + 1 if today.weekday() != 6 else 0)
        start = today - timedelta(days=(today.weekday() + 1) % 7)
        end = start + timedelta(days=6)
        return start, end, f"{start.strftime('%d')} - {end.strftime('%d %B')}"
    if period == "Month":
        start = today.replace(day=1)
        next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
        end = next_month - timedelta(days=1)
        return start, end, today.strftime("%B %Y")
    if period == "Year":
        return today.replace(month=1, day=1), today.replace(month=12, day=31), today.strftime("%Y")
    if period == "Interval" and custom:
        return custom[0], custom[1], f"{custom[0]} - {custom[1]}"
    return date(1900, 1, 1), date(2999, 12, 31), "All time"

def filtered_transactions():
    ss = st.session_state
    start, end, label = period_bounds(ss.period, custom=ss.get("custom_range"))
    txns = [t for t in ss.transactions if start <= t["date"] <= end]
    return txns, label

# ────────────────────────────────────────────────────────────────────────
# SIDEBAR (the app's "hamburger" drawer: accounts / categories / filter)
# ────────────────────────────────────────────────────────────────────────
def sidebar():
    ss = st.session_state
    with st.sidebar:
        st.markdown("### 📖 Menu")

        with st.expander("💼 Accounts", expanded=False):
            for name, info in ss.accounts.items():
                st.write(f"{info['icon']} **{name}** — {fmt(info['balance'])}")
            st.divider()
            new_acc = st.text_input("New account name", key="new_acc_name")
            new_icon = st.text_input("Icon (emoji)", value="🏦", key="new_acc_icon")
            if st.button("Add account"):
                if new_acc and new_acc not in ss.accounts:
                    ss.accounts[new_acc] = {"icon": new_icon or "🏦", "balance": 0.0}
                    st.rerun()
            if st.button("↔ Transfer between accounts"):
                navigate("new_transfer")

        with st.expander("📗 Categories", expanded=False):
            st.caption("EXPENSES")
            for name, icon in ss.expense_categories.items():
                st.write(f"{icon} {name}")
            st.caption("INCOMES")
            for name, icon in ss.income_categories.items():
                st.write(f"{icon} {name}")
            st.divider()
            cat_kind = st.radio("Add to", ["Expense", "Income"], horizontal=True, key="cat_kind")
            cat_name = st.text_input("Category name", key="new_cat_name")
            cat_icon = st.text_input("Icon (emoji)", value="🏷️", key="new_cat_icon")
            if st.button("Add category"):
                if cat_name:
                    target = ss.expense_categories if cat_kind == "Expense" else ss.income_categories
                    target[cat_name] = cat_icon or "🏷️"
                    st.rerun()

        with st.expander("📅 Filter period", expanded=False):
            period = st.radio("Show", ["Day", "Week", "Month", "Year", "All", "Interval"],
                               index=["Day", "Week", "Month", "Year", "All", "Interval"].index(ss.period))
            if period == "Interval":
                d1 = st.date_input("From", value=date.today() - timedelta(days=7))
                d2 = st.date_input("To", value=date.today())
                ss.custom_range = (d1, d2)
            ss.period = period

# ────────────────────────────────────────────────────────────────────────
# HOME PAGE
# ────────────────────────────────────────────────────────────────────────
def donut_chart(txns):
    exp_by_cat = {}
    for t in txns:
        if t["kind"] == "expense":
            exp_by_cat[t["category"]] = exp_by_cat.get(t["category"], 0) + t["amount"]

    total_income = sum(t["amount"] for t in txns if t["kind"] == "income")
    total_expense = sum(t["amount"] for t in txns if t["kind"] == "expense")

    try:
        if exp_by_cat:
            labels = list(exp_by_cat.keys())
            values = list(exp_by_cat.values())
            icons = [st.session_state.expense_categories.get(l, "") for l in labels]
            fig = go.Figure(data=[go.Pie(
                labels=[f"{i} {l}" for i, l in zip(icons, labels)],
                values=values,
                hole=0.55,
            )])
        else:
            # Minimal placeholder pie — avoids version-sensitive kwargs
            fig = go.Figure(data=[go.Pie(labels=["No data"], values=[1], hole=0.55)])
            fig.update_traces(textinfo="none", hoverinfo="skip",
                               marker=dict(colors=["#CFCFCF"]))

        fig.update_layout(
            showlegend=bool(exp_by_cat), height=340, margin=dict(t=10, b=10, l=10, r=10),
            annotations=[
                dict(text=f"<span style='color:{GREEN_DARK}'>{fmt(total_income)}</span>", x=0.5, y=0.56,
                     font_size=18, showarrow=False),
                dict(text=f"<span style='color:{RED}'>{fmt(total_expense)}</span>", x=0.5, y=0.44,
                     font_size=18, showarrow=False),
            ],
        )
        return fig
    except Exception as e:
        # Never let a charting hiccup crash the whole app — show the real
        # error inline (Streamlit Cloud otherwise redacts it) and fall back
        # to a plain summary so the page still renders.
        st.error(f"Chart error (please share this so it can be fixed): {type(e).__name__}: {e}")
        st.write(f"Income: {fmt(total_income)}  |  Expense: {fmt(total_expense)}")
        return go.Figure()

def home_page():
    ss = st.session_state
    txns, label = filtered_transactions()

    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(f"<div class='app-header'><span>💰 Expense Tracker<br>"
                     f"<span class='app-sub'>All accounts</span></span></div>", unsafe_allow_html=True)
    with c2:
        if st.button("↔", help="New transfer"):
            navigate("new_transfer")

    st.markdown(f"<p style='text-align:center;color:{GREEN_DARK};margin-top:0'>{label}</p>",
                unsafe_allow_html=True)

    st.plotly_chart(donut_chart(txns), use_container_width=True)

    st.caption("Tap a category to add an expense")
    cats = list(ss.expense_categories.items())
    cols = st.columns(4)
    for i, (name, icon) in enumerate(cats):
        with cols[i % 4]:
            if st.button(f"{icon}\n{name}", key=f"cat_{name}"):
                navigate("new_expense", category=name, kind="expense")

    total_balance = sum(a["balance"] for a in ss.accounts.values())
    st.markdown(f"<div class='balance-bar'>Balance {fmt(total_balance)}</div>", unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        st.markdown("<div class='expense-btn'>", unsafe_allow_html=True)
        if st.button("EXPENSE", use_container_width=True):
            navigate("new_expense")
        st.markdown("</div>", unsafe_allow_html=True)
    with b2:
        st.markdown("<div class='income-btn'>", unsafe_allow_html=True)
        if st.button("INCOME", use_container_width=True):
            navigate("new_income")
        st.markdown("</div>", unsafe_allow_html=True)

    if txns:
        st.divider()
        st.caption("Recent transactions")
        df = pd.DataFrame(txns)
        df = df.sort_values("date", ascending=False)
        df_display = df[["date", "kind", "category", "account", "amount", "note"]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("There are no records for this period yet.")

# ────────────────────────────────────────────────────────────────────────
# KEYPAD — styled like the Windows Calculator "Standard" view
# ────────────────────────────────────────────────────────────────────────
def keypad(key_prefix):
    ss = st.session_state
    buf_key = f"{key_prefix}_buffer"
    ss.setdefault(buf_key, "0")

    st.markdown("<div class='calc-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='calc-title'>☰ &nbsp; Standard</div>", unsafe_allow_html=True)
    st.markdown("<div class='calc-memrow'><span>MC &nbsp; MR &nbsp; M+ &nbsp; M− &nbsp; MS</span><span>M▾</span></div>",
                unsafe_allow_html=True)
    st.markdown(f"<div class='calc-display'>{ss[buf_key]}</div>", unsafe_allow_html=True)

    def row(labels, eq_col=None):
        cols = st.columns(len(labels))
        for i, label in enumerate(labels):
            target_col = cols[i]
            if eq_col == i:
                target_col.markdown("<div class='calc-eq'>", unsafe_allow_html=True)
            if target_col.button(label, key=f"{key_prefix}_{label}_{id(labels)}_{i}"):
                _keypad_press(buf_key, label)
                st.rerun()
            if eq_col == i:
                target_col.markdown("</div>", unsafe_allow_html=True)

    row(["%", "CE", "C", "⌫"])
    row(["¹⁄x", "x²", "²√x", "÷"])
    row(["7", "8", "9", "×"])
    row(["4", "5", "6", "−"])
    row(["1", "2", "3", "+"])
    row(["+/-", "0", ".", "="], eq_col=3)

    st.markdown("</div>", unsafe_allow_html=True)

def _keypad_press(buf_key, label):
    ss = st.session_state
    cur = ss[buf_key]
    ops = {"+": "+", "−": "-", "×": "*", "÷": "/"}

    if label == "=":
        try:
            expr = cur
            for sym, py in ops.items():
                expr = expr.replace(sym, py)
            result = eval(expr, {"__builtins__": {}}, {})
            ss[buf_key] = str(round(float(result), 2))
        except Exception:
            ss[buf_key] = "0"
    elif label == "C":
        ss[buf_key] = "0"
    elif label == "CE":
        ss[buf_key] = "0"
    elif label == "⌫":
        ss[buf_key] = cur[:-1] if len(cur) > 1 else "0"
    elif label == "+/-":
        if cur.startswith("-"):
            ss[buf_key] = cur[1:]
        elif cur not in ("0", ""):
            ss[buf_key] = "-" + cur
    elif label == "%":
        try:
            ss[buf_key] = str(round(float(cur) / 100, 4))
        except Exception:
            pass
    elif label == "¹⁄x":
        try:
            ss[buf_key] = str(round(1 / float(cur), 6))
        except Exception:
            pass
    elif label == "x²":
        try:
            ss[buf_key] = str(round(float(cur) ** 2, 4))
        except Exception:
            pass
    elif label == "²√x":
        try:
            ss[buf_key] = str(round(float(cur) ** 0.5, 6))
        except Exception:
            pass
    elif label in ("+", "−", "×", "÷"):
        ss[buf_key] = cur + label
    elif label == ".":
        last_segment = re.split(r"[+\-*/]", cur)[-1]
        if "." not in last_segment:
            ss[buf_key] = cur + "."
    else:  # digit
        ss[buf_key] = label if cur == "0" else cur + label

def current_amount(key_prefix):
    raw = st.session_state.get(f"{key_prefix}_buffer", "0")
    try:
        expr = raw
        for sym, py in {"+": "+", "−": "-", "×": "*", "÷": "/"}.items():
            expr = expr.replace(sym, py)
        return abs(float(eval(expr, {"__builtins__": {}}, {})))
    except Exception:
        return 0.0

# ────────────────────────────────────────────────────────────────────────
# NEW EXPENSE / NEW INCOME
# ────────────────────────────────────────────────────────────────────────
def entry_page(kind):
    ss = st.session_state
    title = "New expense" if kind == "expense" else "New income"
    cats = ss.expense_categories if kind == "expense" else ss.income_categories

    top1, top2 = st.columns([1, 6])
    if top1.button("←", key=f"back_{kind}"):
        navigate("home")
    top2.markdown(f"### {title}")
    st.caption(date.today().strftime("%A, %d %B"))

    account = st.selectbox(
        "Account", list(ss.accounts.keys()),
        format_func=lambda a: f"{ss.accounts[a]['icon']} {a}", key=f"{kind}_account")

    keypad(kind)
    amount = current_amount(kind)
    st.write(f"Amount: **{fmt(amount)}**")

    default_cat = ss.preset_category if ss.preset_category in cats else list(cats.keys())[0]
    category = st.selectbox(
        "Category", list(cats.keys()),
        index=list(cats.keys()).index(default_cat),
        format_func=lambda c: f"{cats[c]} {c}", key=f"{kind}_category")

    note = st.text_input("Note", key=f"{kind}_note")

    if st.button("SAVE", key=f"{kind}_save", use_container_width=True):
        if amount <= 0:
            st.warning("Enter an amount greater than 0.")
        else:
            ss.transactions.append({
                "date": date.today(), "kind": kind, "category": category,
                "account": account, "amount": amount, "note": note,
            })
            if kind == "expense":
                ss.accounts[account]["balance"] -= amount
            else:
                ss.accounts[account]["balance"] += amount
            ss[f"{kind}_buffer"] = "0"
            navigate("home")

# ────────────────────────────────────────────────────────────────────────
# NEW TRANSFER
# ────────────────────────────────────────────────────────────────────────
def transfer_page():
    ss = st.session_state
    top1, top2 = st.columns([1, 6])
    if top1.button("←", key="back_transfer"):
        navigate("home")
    top2.markdown("### New transfer")
    st.caption(date.today().strftime("%A, %d %B"))

    keypad("transfer")
    amount = current_amount("transfer")
    st.write(f"Amount: **{fmt(amount)}**")

    note = st.text_input("Note", key="transfer_note")

    acc_names = list(ss.accounts.keys())
    from_acc = st.selectbox("From", acc_names,
                             format_func=lambda a: f"{ss.accounts[a]['icon']} {a} ({fmt(ss.accounts[a]['balance'])})",
                             key="transfer_from")
    st.markdown("<div style='text-align:center;font-size:22px;'>⬇</div>", unsafe_allow_html=True)
    to_acc = st.selectbox("To", acc_names,
                           format_func=lambda a: f"{ss.accounts[a]['icon']} {a} ({fmt(ss.accounts[a]['balance'])})",
                           index=min(1, len(acc_names) - 1), key="transfer_to")

    if st.button("SAVE TRANSFER", use_container_width=True):
        if amount <= 0:
            st.warning("Enter an amount greater than 0.")
        elif from_acc == to_acc:
            st.warning("Choose two different accounts.")
        else:
            ss.accounts[from_acc]["balance"] -= amount
            ss.accounts[to_acc]["balance"] += amount
            ss.transactions.append({
                "date": date.today(), "kind": "transfer",
                "category": "Transfer", "account": f"{from_acc} → {to_acc}",
                "amount": amount, "note": note,
            })
            ss["transfer_buffer"] = "0"
            navigate("home")

# ────────────────────────────────────────────────────────────────────────
# ROUTER
# ────────────────────────────────────────────────────────────────────────
sidebar()

page = st.session_state.page
if page == "home":
    home_page()
elif page == "new_expense":
    entry_page("expense")
elif page == "new_income":
    entry_page("income")
elif page == "new_transfer":
    transfer_page()
else:
    home_page()