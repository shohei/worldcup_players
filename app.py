import streamlit as st
import pandas as pd
import pydeck as pydeck

st.set_page_config(page_title="2026 FIFA W杯 代表選手マップ", layout="wide")

st.title("2026 FIFA ワールドカップ 代表選手 所属クラブマップ")
st.caption("各国代表選手がどのクラブに所属しているかを世界地図上に表示します")


@st.cache_data
def load_data():
    players = pd.read_csv("players.csv")
    clubs = pd.read_csv("club_coords.csv")
    clubs = clubs.drop_duplicates(subset=["club"], keep="first")
    merged = players.merge(clubs, on="club", how="left")
    return merged


df = load_data()

unmatched = df[df["lat"].isna()]["club"].unique()
if len(unmatched) > 0:
    st.sidebar.warning(f"座標未登録クラブ: {len(unmatched)}件")

df = df.dropna(subset=["lat", "lng"])

countries = sorted(df["country"].unique())

selected_country = st.sidebar.selectbox(
    "代表チームを選択",
    ["すべて"] + countries,
    index=0,
)

if selected_country == "すべて":
    filtered = df
else:
    filtered = df[df["country"] == selected_country]

club_league_filter = st.sidebar.selectbox(
    "所属クラブの国で絞り込み",
    ["すべて"] + sorted(filtered["club_country"].dropna().unique()),
    index=0,
)
if club_league_filter != "すべて":
    filtered = filtered[filtered["club_country"] == club_league_filter]

grouped = (
    filtered.groupby(["club", "lat", "lng", "city", "club_country"])
    .agg(
        player_count=("player_name", "size"),
        players=("player_name", lambda x: "\n".join(x)),
        countries=("country", lambda x: ", ".join(sorted(set(x)))),
    )
    .reset_index()
)

country_colors = {}
import hashlib
for c in countries:
    h = int(hashlib.md5(c.encode()).hexdigest()[:6], 16)
    country_colors[c] = [(h >> 16) & 0xFF, (h >> 8) & 0xFF, h & 0xFF]


def get_color(countries_str):
    clist = [c.strip() for c in countries_str.split(",")]
    if len(clist) == 1 and clist[0] in country_colors:
        return country_colors[clist[0]]
    return [65, 105, 225]


grouped["color"] = grouped["countries"].apply(get_color)
grouped["radius"] = grouped["player_count"].apply(lambda x: max(x * 12000, 20000))

layer = pydeck.Layer(
    "ScatterplotLayer",
    data=grouped,
    get_position=["lng", "lat"],
    get_radius="radius",
    get_fill_color="color",
    pickable=True,
    opacity=0.7,
    stroked=True,
    get_line_color=[0, 0, 0],
    line_width_min_pixels=1,
)

if selected_country == "すべて":
    view = pydeck.ViewState(latitude=30, longitude=0, zoom=1.5, pitch=0)
else:
    avg_lat = filtered["lat"].mean()
    avg_lng = filtered["lng"].mean()
    view = pydeck.ViewState(latitude=avg_lat, longitude=avg_lng, zoom=3, pitch=0)

tooltip = {
    "html": "<b>{club}</b><br/>{city}, {club_country}<br/>選手数: {player_count}<br/>代表: {countries}<br/><br/>{players}",
    "style": {
        "backgroundColor": "rgba(0,0,0,0.8)",
        "color": "white",
        "fontSize": "12px",
        "padding": "8px",
        "maxWidth": "350px",
        "whiteSpace": "pre-wrap",
    },
}

deck = pydeck.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style="mapbox://styles/mapbox/light-v11",
)

st.pydeck_chart(deck, use_container_width=True, height=600)

st.subheader("統計")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("選手数", len(filtered))
with col2:
    st.metric("代表チーム数", filtered["country"].nunique())
with col3:
    st.metric("所属クラブ数", filtered["club"].nunique())
with col4:
    st.metric("所属クラブの国数", filtered["club_country"].nunique())

st.subheader("所属クラブの国別分布")

country_dist = filtered.groupby("club_country").size().reset_index(name="選手数")
country_dist = country_dist.sort_values("選手数", ascending=False)
st.bar_chart(country_dist.set_index("club_country")["選手数"])

st.subheader("選手一覧")

display_df = filtered[["country", "player_name", "club", "city", "club_country"]].copy()
display_df.columns = ["代表", "選手名", "所属クラブ", "都市", "クラブの国"]
display_df = display_df.sort_values(["代表", "選手名"])
st.dataframe(display_df, use_container_width=True, hide_index=True, height=400)
