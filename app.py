import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

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

club_countries = sorted(filtered["club_country"].dropna().unique())
club_league_filter = st.sidebar.selectbox(
    "所属クラブの国で絞り込み",
    ["すべて"] + club_countries,
    index=0,
)
if club_league_filter != "すべて":
    filtered = filtered[filtered["club_country"] == club_league_filter]

grouped = (
    filtered.groupby(["club", "lat", "lng", "city", "club_country"])
    .agg(
        player_count=("player_name", "size"),
        players=("player_name", list),
        countries=("country", lambda x: sorted(set(x))),
    )
    .reset_index()
)

if selected_country == "すべて":
    center = [30, 0]
    zoom = 2
else:
    center = [filtered["lat"].mean(), filtered["lng"].mean()]
    zoom = 3

m = folium.Map(location=center, zoom_start=zoom, tiles="CartoDB positron")

marker_cluster = MarkerCluster(
    options={"maxClusterRadius": 35, "disableClusteringAtZoom": 6}
).add_to(m)

for _, row in grouped.iterrows():
    player_list = "<br>".join(
        [f"・{p}" for p in row["players"]]
    )
    country_list = ", ".join(row["countries"])
    popup_html = f"""
    <div style="min-width:200px; max-width:300px; font-family:sans-serif; font-size:12px;">
        <b style="font-size:14px;">{row['club']}</b><br>
        <span style="color:#666;">{row['city']}, {row['club_country']}</span><br>
        <hr style="margin:4px 0;">
        <b>代表: {country_list}</b><br>
        <b>選手数: {row['player_count']}</b><br>
        <hr style="margin:4px 0;">
        {player_list}
    </div>
    """

    radius = max(row["player_count"] * 3, 5)

    folium.CircleMarker(
        location=[row["lat"], row["lng"]],
        radius=radius,
        popup=folium.Popup(popup_html, max_width=320),
        tooltip=f"{row['club']} ({row['player_count']}人)",
        color="#2B5EA7",
        fill=True,
        fill_color="#4A90D9",
        fill_opacity=0.7,
        weight=1,
    ).add_to(marker_cluster)

st_folium(m, use_container_width=True, height=600, returned_objects=[])

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
