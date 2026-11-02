import streamlit as st
from src.discovery import discover_profiles, build_boolean_query
from src.scoring import score_profile
from src.storage import init_db, is_contacted, get_daily_count, mark_contacted
from src.dispatch import handoff_html

st.set_page_config(page_title="Learner Discovery Agent", page_icon="🎯", layout="wide")
init_db()
st.title("🎯 LinkedIn Learner Discovery & Outreach Agent")
st.caption("Publicly indexed profile discovery, relevance scoring, and human-reviewed outreach.")
st.info("No LinkedIn login, automated scraping, or automatic message sending. Review all profiles and drafts yourself.")
with st.sidebar:
    bucket=st.selectbox("Target bucket",["Students / Freshers","Early Career 1–2 YOE","Career Switchers"])
    defaults={"Students / Freshers":"Final Year B.Tech AI engineer","Early Career 1–2 YOE":"Associate Software Engineer Python","Career Switchers":"QA to AI learning GenAI"}
    keywords=st.text_input("Keywords",defaults[bucket])
    mock=st.toggle("Offline demo mode (no API required)",True)
    limit=st.slider("Maximum profiles",3,10,10)
    search=st.button("🔎 Discover profiles",type="primary",use_container_width=True)
st.subheader("Boolean X-Ray query")
st.code(build_boolean_query(bucket,keywords))
if "profiles" not in st.session_state: st.session_state.profiles=[]
if "scored" not in st.session_state: st.session_state.scored={}
if search:
    try:
        st.session_state.profiles=discover_profiles(bucket,keywords,mock,limit)
        st.session_state.scored={}
        if not st.session_state.profiles: st.warning("No profiles found. Try other keywords or offline mode.")
    except Exception as e: st.error(str(e))
profiles=st.session_state.profiles
if profiles:
    count=get_daily_count()
    a,b,c=st.columns(3); a.metric("Profiles",len(profiles)); b.metric("Handoffs today",f"{count}/15"); c.metric("Already contacted",sum(is_contacted(p["url"]) for p in profiles))
    for i,p in enumerate(profiles):
        url=p.get("url","")
        with st.container(border=True):
            st.markdown("### "+p.get("name","Unknown"))
            st.write(p.get("headline","")); st.caption(p.get("snippet",""))
            st.markdown(f"[Open public profile]({url})")
            if is_contacted(url): st.warning("Already marked as handed off.")
            if st.button("✨ Score & draft",key=f"score{i}"): st.session_state.scored[url]=score_profile(p)
            r=st.session_state.scored.get(url)
            if r:
                x,y=st.columns([1,2])
                with x:
                    st.metric("Relevance",f'{r["relevance_score"]}/10'); st.write("Persona: "+r["detected_persona"]); st.caption(r["reasoning"]); st.caption(r["generator"])
                with y:
                    note=st.text_area("Connection note (under 300 characters)",r["connection_note"],max_chars=299,key=f"note{i}")
                    dm=st.text_area("Follow-up DM (under 100 words)",r["follow_up_dm"],key=f"dm{i}")
                    st.caption(f"{len(note)} characters · {len(dm.split())} words")
                    if len(note)>=300 or len(dm.split())>=100: st.error("Please shorten the message to meet the limits.")
                    elif is_contacted(url): st.caption("Already in local contact log.")
                    elif get_daily_count()>=15: st.error("Daily handoff limit reached.")
                    else:
                        st.components.v1.html(handoff_html(note, url, p.get("name", ""), p.get("headline", "")), height=60)
                        if st.button("Mark as handed off",key=f"mark{i}"):
                            try: mark_contacted(url,note); st.success("Handoff recorded (not a confirmed message send)."); st.rerun()
                            except Exception as e: st.error(str(e))
st.divider()
st.caption("Mock URLs are placeholders. External API providers may process submitted profile text under their own policies.")
