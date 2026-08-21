"""
Monefy-style Expense Tracker — Streamlit Clone
------------------------------------------------
A single-file Streamlit app that recreates the core flows seen in the
Monefy budgeting app screenshots:
  - Home screen: donut chart of spending by category, category grid,
    balance bar, EXPENSE / INCOME buttons
  - New expense / New income: numeric keypad + account + category + note
  - New transfer: move money between accounts
  - Accounts drawer: manage accounts, see balances
  - Categories drawer: manage expense & income categories
  - Filter drawer: Day / Week / Month / Year / All / Interval / Choose date

Run with:  streamlit run monefy_clone.py
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

# ────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + THEME
# ────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Monefy", page_icon="💰", layout="centered")

GREEN = "#6FBF8B"
GREEN_DARK = "#5CAE7A"
RED = "#E27272"
BG = "#EAF7EE"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG}; }}
    div.block-container {{ padding-top: 1rem; max-width: 480px; }}
    .monefy-header {{
        background-color: {GREEN}; color: white; padding: 14px 18px;
        border-radius: 8px; font-size: 22px; font-family: cursive;
        display:flex; justify-content:space-between; align-items:center;
        margin-bottom: 6px;
    }}
    .monefy-sub {{ font-size:13px; opacity:0.9; }}
    .balance-bar {{
        background-color:{GREEN}; color:white; text-align:center;
        padding:14px; border-radius:6px; font-size:18px; font-weight:600;
        margin: 14px 0;
    }}
    .amount-box {{
        background-color:{GREEN}; color:white; text-align:right;
        padding:22px 16px; border-radius:8px; font-size:34px;
        border: 1px solid {GREEN_DARK}; margin-bottom: 10px;
    }}
    div.stButton > button {{
        border-radius: 6px; border: 1px solid {GREEN}; color:{GREEN_DARK};
        background-color: white;
    }}
    div.stButton > button:hover {{ border-color:{GREEN_DARK}; color:white; background-color:{GREEN}; }}
    .expense-btn button {{ border-color:{RED} !important; color:{RED} !important; }}
    .income-btn button {{ border-color:{GREEN} !important; color:{GREEN_DARK} !important; }}
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

def go(page, **preset):
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
                go("new_transfer")

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

    if exp_by_cat:
        labels = list(exp_by_cat.keys())
        values = list(exp_by_cat.values())
        icons = [st.session_state.expense_categories.get(l, "") for l in labels]
        fig = go.Figure(data=[go.Pie(
            labels=[f"{i} {l}" for i, l in zip(icons, labels)],
            values=values, hole=0.55,
            marker=dict(line=dict(color=BG, width=2)),
        )])
    else:
        fig = go.Figure(data=[go.Pie(labels=["No data"], values=[1], hole=0.55,
                                      marker=dict(colors=["#CFCFCF"]))])
        fig.update_traces(textinfo="none", hoverinfo="skip")

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

def home_page():
    ss = st.session_state
    txns, label = filtered_transactions()

    c1, c2 = st.columns([5, 1])
    with c1:
        st.markdown(f"<div class='monefy-header'><span><i>Monefy</i><br>"
                     f"<span class='monefy-sub'>All accounts</span></span></div>", unsafe_allow_html=True)
    with c2:
        if st.button("↔", help="New transfer"):
            go("new_transfer")

    st.markdown(f"<p style='text-align:center;color:{GREEN_DARK};margin-top:0'>{label}</p>",
                unsafe_allow_html=True)

    st.plotly_chart(donut_chart(txns), use_container_width=True)

    st.caption("Tap a category to add an expense")
    cats = list(ss.expense_categories.items())
    cols = st.columns(4)
    for i, (name, icon) in enumerate(cats):
        with cols[i % 4]:
            if st.button(f"{icon}\n{name}", key=f"cat_{name}"):
                go("new_expense", category=name, kind="expense")

    total_balance = sum(a["balance"] for a in ss.accounts.values())
    st.markdown(f"<div class='balance-bar'>Balance {fmt(total_balance)}</div>", unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    with b1:
        st.markdown("<div class='expense-btn'>", unsafe_allow_html=True)
        if st.button("EXPENSE", use_container_width=True):
            go("new_expense")
        st.markdown("</div>", unsafe_allow_html=True)
    with b2:
        st.markdown("<div class='income-btn'>", unsafe_allow_html=True)
        if st.button("INCOME", use_container_width=True):
            go("new_income")
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
# KEYPAD (calculator-style amount entry, like the screenshots)
# ────────────────────────────────────────────────────────────────────────
def keypad(key_prefix):
    ss = st.session_state
    buf_key = f"{key_prefix}_buffer"
    ss.setdefault(buf_key, "0")

    st.markdown(f"<div class='amount-box'>{ss[buf_key]}</div>", unsafe_allow_html=True)

    rows = [["1", "2", "3", "+"], ["4", "5", "6", "-"],
            ["7", "8", "9", "×"], [".", "0", "=", "÷"]]
    for r in rows:
        cols = st.columns(4)
        for i, label in enumerate(r):
            if cols[i].button(label, key=f"{key_prefix}_{label}_{r.index(label)}_{rows.index(r)}"):
                _keypad_press(buf_key, label)
                st.rerun()
    if st.button("⌫ Clear", key=f"{key_prefix}_clear"):
        ss[buf_key] = "0"
        st.rerun()

def _keypad_press(buf_key, label):
    ss = st.session_state
    cur = ss[buf_key]
    if label == "=":
        try:
            expr = cur.replace("×", "*").replace("÷", "/")
            result = eval(expr, {"__builtins__": {}}, {})
            ss[buf_key] = str(round(float(result), 2))
        except Exception:
            ss[buf_key] = "0"
    elif label in ("+", "-", "×", "÷"):
        ss[buf_key] = cur + label
    elif label == ".":
        ss[buf_key] = cur + "."
    else:  # digit
        ss[buf_key] = label if cur == "0" else cur + label

def current_amount(key_prefix):
    raw = st.session_state.get(f"{key_prefix}_buffer", "0")
    try:
        expr = raw.replace("×", "*").replace("÷", "/")
        return float(eval(expr, {"__builtins__": {}}, {}))
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
        go("home")
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
            go("home")

# ────────────────────────────────────────────────────────────────────────
# NEW TRANSFER
# ────────────────────────────────────────────────────────────────────────
def transfer_page():
    ss = st.session_state
    top1, top2 = st.columns([1, 6])
    if top1.button("←", key="back_transfer"):
        go("home")
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
            go("home")

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
