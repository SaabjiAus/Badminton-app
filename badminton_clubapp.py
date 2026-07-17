# ==============================================================================
# 🏸 BADMINTON CLUBHOUSE + 🍽️ MEAL PLANNER ENGINE - PRODUCTION BUILD
# ==============================================================================

import streamlit as st
import random
import uuid
import pandas as pd
import itertools
import datetime
import copy
import json
from supabase import create_client, Client

# --- GLOBAL STAGE INITIALIZATION ---
st.set_page_config(
    page_title="Clubhouse Cloud",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==============================================================================
# 💾 SECTION 1: SUPABASE LIVE CLOUD STORAGE MANAGEMENT FUNCTIONS
# ==============================================================================

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_local_data(room_name):
    try:
        response = supabase_client.table("clubhouse_rooms").select("room_data").eq("room_id", room_name).execute()
        if response.data:
            data = response.data[0]["room_data"]
            if "total_visits" not in data: data["total_visits"] = 0        
            data["total_visits"] += 1           
            
            updated = False
            for key, default_val in [
                ("players", []), ("teams", []), ("matches", []), 
                ("expenses", {}), ("ind_leaderboard", {}), ("team_leaderboard", {}),
                ("match_history", []), ("meals", []),
                ("created_at", str(datetime.date.today()))
            ]:
                if key not in data:             
                    data[key] = default_val     
                    updated = True              
            
            if updated: save_local_data(room_name, data)            
            return data
        
        default_data = {
            "players": [], "teams": [], "matches": [], "expenses": {},             
            "ind_leaderboard": {}, "team_leaderboard": {}, "match_history": [],
            "meals": [],
            "created_at": str(datetime.date.today()), "total_visits": 1           
        }
        supabase_client.table("clubhouse_rooms").insert({"room_id": room_name, "room_data": default_data}).execute()
        return default_data
        
    except Exception as e:
        st.error(f"🚨 Supabase Fetch Failure: {e}")
        return {"players": [], "teams": [], "matches": [], "expenses": {}, "meals": []}

def save_local_data(room_name, data):
    try:
        supabase_client.table("clubhouse_rooms").update({"room_data": data, "updated_at": "now()"}).eq("room_id", room_name).execute()
    except Exception as e:
        st.error(f"🚨 Supabase Update Sync Failure: {e}")

# ==============================================================================
# 🔑 SECTION 2: ACCESS CONTROL GATEWAY INTERFACE (STICKY URLs)
# ==============================================================================

if "room_id" not in st.session_state:
    if "room" in st.query_params:
        st.session_state.room_id = st.query_params["room"]
    else:
        st.title("🏸 Clubhouse Portal & 🍽️ Diet Planner Gateway") 
        st.markdown("Enter a sports club code to manage matches, or enter the dedicated meal code below.")
        room_input = st.text_input("Access Code (e.g., SUNDAY-SMASH or MEAL-PLANNER)", "").strip().upper()
        
        if st.button("Enter Dashboard", type="primary"): 
            if room_input == "ADMIN-STATS":              
                st.session_state.room_id = "ADMIN_PANEL"
                st.query_params["room"] = "ADMIN_PANEL"
                st.rerun()                               
            elif room_input == "MEAL-PLANNER":
                st.session_state.room_id = "MEAL_PLANNER_PANEL"
                st.query_params["room"] = "MEAL_PLANNER_PANEL"
                st.rerun()
            elif room_input:                             
                st.session_state.room_id = room_input
                st.query_params["room"] = room_input
                st.rerun()                               
        st.stop()                                       

room_code = st.session_state.room_id

if "room_data" not in st.session_state and room_code not in ["ADMIN_PANEL", "MEAL_PLANNER_PANEL"]:
    st.session_state.room_data = get_local_data(room_code) 

# ==============================================================================
# 🛡️ SECTION 3: SYSTEM AUDIT INSIGHTS (ADMIN PANEL)
# ==============================================================================

if st.session_state.room_id == "ADMIN_PANEL":
    st.title("🛡️ Central Cloud Analytics & Database Control")
    if st.button("⬅️ Log Out of Admin Mode"): 
        del st.session_state.room_id                        
        if "room" in st.query_params: del st.query_params["room"]
        if "tab" in st.query_params: del st.query_params["tab"]
        st.rerun()                                          
        
    st.markdown("---")                                      
    admin_summary_data = []
    room_list = []
    try:
        response = supabase_client.table("clubhouse_rooms").select("room_id", "room_data").execute()
        if response.data:
            for row in response.data:                              
                room_payload = row["room_data"]
                room_id_name = row["room_id"]
                room_list.append(room_id_name)
                admin_summary_data.append({
                    "Room Code": room_id_name, 
                    "Created": room_payload.get("created_at", "Legacy"),
                    "Visits": room_payload.get("total_visits", 1), 
                    "Players": len(room_payload.get("players", [])), 
                    "Matches": len(room_payload.get("matches", [])),
                    "Meals Logged": len(room_payload.get("meals", []))
                })
    except Exception as e:
        st.error(f"Admin Data Retrieval Failure: {e}")
        
    st.metric(label="Total Created Activity Rooms", value=len(admin_summary_data))
    if admin_summary_data:                                  
        st.dataframe(pd.DataFrame(admin_summary_data), use_container_width=True)
        
    st.markdown("### 🛠️ Database Management (Edit / Delete Rooms)")
    
    if room_list:
        selected_del_room = st.selectbox("Select a Room to Manage:", room_list)
        
        if selected_del_room:
            room_to_edit_resp = supabase_client.table("clubhouse_rooms").select("room_data").eq("room_id", selected_del_room).execute()
            if room_to_edit_resp.data:
                raw_json = room_to_edit_resp.data[0]["room_data"]
                edited_json_str = st.text_area(f"Edit Raw JSON Data for '{selected_del_room}':", value=json.dumps(raw_json, indent=4), height=400)
                
                col_save, col_del = st.columns(2)
                with col_save:
                    if st.button("💾 Save Database Changes", type="primary", use_container_width=True):
                        try:
                            updated_dict = json.loads(edited_json_str)
                            supabase_client.table("clubhouse_rooms").update({"room_data": updated_dict}).eq("room_id", selected_del_room).execute()
                            st.success(f"Successfully updated database for {selected_del_room}!")
                        except Exception as e:
                            st.error(f"Invalid JSON Format: {e}")
                            
                with col_del:
                    if st.button("🚨 Delete Room Entirely", use_container_width=True):
                        try:
                            supabase_client.table("clubhouse_rooms").delete().eq("room_id", selected_del_room).execute()
                            st.success(f"Room {selected_del_room} was deleted permanently!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete: {e}")
    st.stop()

# ==============================================================================
# 🍽️ SECTION: DEDICATED MEAL PLANNER & CALENDAR WORKSPACE
# ==============================================================================

if st.session_state.room_id == "MEAL_PLANNER_PANEL":
    if "meal_data" not in st.session_state:
        st.session_state.meal_data = get_local_data("MEAL_PLANNER_PANEL")
        
    st.title("🍽️ Smart Predictive Meal Planner & Calendar")
    st.caption("Log what you eat now to dynamically generate next month's proactive recommendations.")
    
    if st.button("⬅️ Exit Meal Workspace"):
        del st.session_state.room_id
        if "meal_data" in st.session_state: del st.session_state.meal_data
        if "room" in st.query_params: del st.query_params["room"]
        st.rerun()
        
    st.markdown("---")
    
    def compute_next_month_date(current_date):
        year = current_date.year
        month = current_date.month + 1
        if month > 12:
            month = 1
            year += 1
        day = current_date.day
        while True:
            try:
                return datetime.date(year, month, day)
            except ValueError:
                day -= 1

    with st.expander("✨ Log a New Meal Entry", expanded=True):
        with st.form("add_meal_form", clear_on_submit=True):
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                meal_name = st.text_input("What did you eat?", placeholder="e.g., Grilled Chicken Rice Bowl").strip()
                meal_type = st.selectbox("Meal Category:", ["Breakfast", "Lunch", "Dinner", "Snack"])
            with col_m2:
                meal_date = st.date_input("Date Eaten:", datetime.date.today())
                meal_time = st.time_input("Time Eaten:", datetime.datetime.now().time())
                
            submit_meal = st.form_submit_button("Log Meal & Project to Next Month", type="primary")
            
            if submit_meal:
                if not meal_name:
                    st.error("Please provide a name for your meal record.")
                else:
                    meal_id = str(uuid.uuid4())
                    timestamp_str = datetime.datetime.combine(meal_date, meal_time).isoformat()
                    
                    next_month_date = compute_next_month_date(meal_date)
                    projection_timestamp_str = datetime.datetime.combine(next_month_date, meal_time).isoformat()
                    
                    new_entry = {
                        "id": meal_id, "name": meal_name, "type": meal_type,
                        "timestamp": timestamp_str, "is_projection": False
                    }
                    projected_entry = {
                        "id": str(uuid.uuid4()), "name": meal_name, "type": meal_type,
                        "timestamp": projection_timestamp_str, "is_projection": True, "parent_id": meal_id
                    }
                    
                    st.session_state.meal_data["meals"].append(new_entry)
                    st.session_state.meal_data["meals"].append(projected_entry)
                    save_local_data("MEAL_PLANNER_PANEL", st.session_state.meal_data)
                    st.success(f"Successfully logged '{meal_name}' and projected its schedule for {next_month_date}!")
                    st.rerun()

    all_meals = st.session_state.meal_data.get("meals", [])
    
    if all_meals:
        st.markdown("### 📊 Interactive Diet Timeline & Calendar Workspace")
        
        # Interactive filters
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            cat_filter = st.selectbox("Filter Workspace by Category:", ["All", "Breakfast", "Lunch", "Dinner", "Snack"])
        with col_f2:
            status_filter = st.radio("Filter Workspace by Status:", ["All Records", "✅ Logged Actual Eaten", "🔮 Projected Next Month"], horizontal=True)
            
        filtered_meals = []
        for m in all_meals:
            dt = datetime.datetime.fromisoformat(m["timestamp"])
            is_proj = m.get("is_projection", False)
            
            if cat_filter != "All" and m["type"] != cat_filter:
                continue
            if status_filter == "✅ Logged Actual Eaten" and is_proj:
                continue
            if status_filter == "🔮 Projected Next Month" and not is_proj:
                continue
                
            filtered_meals.append({
                "Date": dt.date(),
                "Time": dt.time().strftime("%H:%M"),
                "Meal": m["name"],
                "Category": m["type"],
                "Status": "🔮 Projected" if is_proj else "✅ Eaten"
            })
            
        if filtered_meals:
            f_df = pd.DataFrame(filtered_meals).sort_values(by=["Date", "Time"], ascending=True)
            
            # Draw beautiful timeline cards grouped by date
            for date, group in f_df.groupby("Date"):
                st.markdown(f"##### 🗓️ {date.strftime('%A, %b %d, %Y')}")
                num_items = len(group)
                cols = st.columns(min(4, num_items))
                for idx, (_, row) in enumerate(group.iterrows()):
                    col_idx = idx % len(cols)
                    with cols[col_idx]:
                        emoji = "🥞" if row["Category"] == "Breakfast" else "🍲" if row["Category"] == "Lunch" else "🥩" if row["Category"] == "Dinner" else "🍿"
                        bg_color = "#f0fdf4" if row["Status"] == "✅ Eaten" else "#f5f3ff"
                        border_color = "#bbf7d0" if row["Status"] == "✅ Eaten" else "#ddd6fe"
                        text_color = "#166534" if row["Status"] == "✅ Eaten" else "#5b21b6"
                        
                        st.markdown(
                            f"""
                            <div style="border: 1px solid {border_color}; padding: 12px; border-radius: 8px; background-color: {bg_color}; margin-bottom: 10px;">
                                <div style="font-size: 1.3em; margin-bottom: 4px;">{emoji}</div>
                                <div style="font-weight: 600; color: #1f2937;">{row['Meal']}</div>
                                <div style="font-size: 0.85em; color: #4b5563; margin-top: 4px;">{row['Time']} • {row['Category']}</div>
                                <div style="margin-top: 8px; font-size: 0.8em; font-weight: 700; color: {text_color};">{row['Status']}</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
        else:
            st.info("No logs match the selected filter configuration.")

        st.markdown("### 🛠️ Modify & Delete Logged Entries")
        
        meal_df_list = []
        for m in all_meals:
            dt = datetime.datetime.fromisoformat(m["timestamp"])
            meal_df_list.append({
                "ID": m["id"], "Meal Name": m["name"], "Category": m["type"],
                "Date": dt.date(), "Time": dt.time().strftime("%H:%M"),
                "Type": "🔮 Projected Next Month" if m.get("is_projection", False) else "✅ Logged Actual Eaten"
            })
            
        df_display = pd.DataFrame(meal_df_list).sort_values(by=["Date", "Time"], ascending=False)
        st.dataframe(df_display.drop(columns=["ID"]), use_container_width=True)
        
        target_options = {f"[{row['Type']}] {row['Meal Name']} ({row['Date']} @ {row['Time']})": row["ID"] for _, row in df_display.iterrows()}
        selected_target_label = st.selectbox("Select a Record to Edit or Remove:", list(target_options.keys()))
        selected_id = target_options[selected_target_label]
        
        target_obj = next((m for m in all_meals if m["id"] == selected_id), None)
        
        if target_obj:
            col_ed1, col_ed2 = st.columns(2)
            with col_ed1:
                edit_name = st.text_input("Modify Name Value:", value=target_obj["name"], key="edit_name")
                edit_type = st.selectbox("Modify Category Selection:", ["Breakfast", "Lunch", "Dinner", "Snack"], index=["Breakfast", "Lunch", "Dinner", "Snack"].index(target_obj["type"]), key="edit_type")
            with col_ed2:
                current_dt = datetime.datetime.fromisoformat(target_obj["timestamp"])
                edit_date = st.date_input("Modify Date Value:", value=current_dt.date(), key="edit_date")
                edit_time = st.time_input("Modify Time Value:", value=current_dt.time(), key="edit_time")
                
            col_actions = st.columns([1, 1, 2])
            with col_actions[0]:
                if st.button("💾 Apply Modifications", type="primary", use_container_width=True):
                    target_obj["name"] = edit_name
                    target_obj["type"] = edit_type
                    target_obj["timestamp"] = datetime.datetime.combine(edit_date, edit_time).isoformat()
                    
                    if not target_obj.get("is_projection", False):
                        nxt_d = compute_next_month_date(edit_date)
                        proj_twin = next((m for m in all_meals if m.get("parent_id") == target_obj["id"]), None)
                        if proj_twin:
                            proj_twin["name"] = edit_name
                            proj_twin["type"] = edit_type
                            proj_twin["timestamp"] = datetime.datetime.combine(nxt_d, edit_time).isoformat()
                            
                    save_local_data("MEAL_PLANNER_PANEL", st.session_state.meal_data)
                    st.toast("Entry modified successfully!")
                    st.rerun()
                    
            with col_actions[1]:
                if st.button("🗑️ Remove Entry", use_container_width=True):
                    st.session_state.meal_data["meals"] = [m for m in all_meals if m["id"] != selected_id and m.get("parent_id") != selected_id]
                    save_local_data("MEAL_PLANNER_PANEL", st.session_state.meal_data)
                    st.toast("Record wiped successfully!")
                    st.rerun()
    else:
        st.info("No meals logged yet. Use the form above to record your first meal entry!")

    st.stop()

# ==============================================================================
# 🗂️ SECTION 4: MAIN DASHBOARD LAYOUT & HELPER FUNCTIONS
# ==============================================================================

col1, col2 = st.columns([4, 1])                             
with col1:
    st.title(f"🏸 Match & Tournament Hub")
    st.caption(f"Active Live Cloud Room: **{room_code}**")      
with col2:
    if st.button("Change Room / Exit", use_container_width=True): 
        del st.session_state.room_id                        
        if "room_data" in st.session_state: del st.session_state.room_data                  
        if "room" in st.query_params: del st.query_params["room"]
        if "tab" in st.query_params: del st.query_params["tab"] 
        if "active_tab" in st.session_state: del st.session_state.active_tab
        st.rerun()

st.markdown("---")

def generate_and_lock_teams(match_format, active_players):
    shuffled_pool = list(active_players)                               
    random.shuffle(shuffled_pool)                               
    st.session_state.room_data["teams"] = []                    
    
    if match_format == "Singles":                               
        for p in shuffled_pool:                                 
            st.session_state.room_data["teams"].append([p])     
    else:                                                       
        while len(shuffled_pool) >= 2:                          
            st.session_state.room_data["teams"].append([shuffled_pool.pop(), shuffled_pool.pop()]) 
        if len(shuffled_pool) == 1:
            odd_player = shuffled_pool.pop()
            for other_player in active_players:
                if other_player != odd_player:
                    st.session_state.room_data["teams"].append([odd_player, other_player])
    save_local_data(room_code, st.session_state.room_data)      

def log_match_to_history(match):
    ind_lb = st.session_state.room_data["ind_leaderboard"]      
    team_lb = st.session_state.room_data["team_leaderboard"]    
    
    t_a_name = " & ".join(sorted(match["team_a"]))               
    t_b_name = " & ".join(sorted(match["team_b"]))               
    
    if t_a_name not in team_lb: team_lb[t_a_name] = {"Wins": 0, "Losses": 0, "Points": 0, "Grand Finals Won": 0}
    if t_b_name not in team_lb: team_lb[t_b_name] = {"Wins": 0, "Losses": 0, "Points": 0, "Grand Finals Won": 0}
    
    if "Losses" not in team_lb[t_a_name]: team_lb[t_a_name]["Losses"] = 0
    if "Losses" not in team_lb[t_b_name]: team_lb[t_b_name]["Losses"] = 0
    if "Grand Finals Won" not in team_lb[t_a_name]: team_lb[t_a_name]["Grand Finals Won"] = 0
    if "Grand Finals Won" not in team_lb[t_b_name]: team_lb[t_b_name]["Grand Finals Won"] = 0
        
    for p in match["team_a"] + match["team_b"]:
        if p not in ind_lb:
            ind_lb[p] = {"Wins": 0, "Losses": 0, "Points": 0, "Singles Played": 0, "Doubles Played": 0, "Grand Finals Won": 0}
        if "Losses" not in ind_lb[p]: ind_lb[p]["Losses"] = 0
        
    team_lb[t_a_name]["Points"] += match["score_a"]             
    team_lb[t_b_name]["Points"] += match["score_b"]             
    for p in match["team_a"]: ind_lb[p]["Points"] += match["score_a"] 
    for p in match["team_b"]: ind_lb[p]["Points"] += match["score_b"] 
    
    is_singles = len(match["team_a"]) == 1
    is_doubles = len(match["team_a"]) == 2
    is_gf = match.get("is_final", False) or "GRAND FINAL" in str(match.get("type", "")).upper()
    
    for p in match["team_a"] + match["team_b"]:
        if is_singles: ind_lb[p]["Singles Played"] += 1
        elif is_doubles: ind_lb[p]["Doubles Played"] += 1

    if match["score_a"] > match["score_b"]:                     
        team_lb[t_a_name]["Wins"] += 1
        team_lb[t_b_name]["Losses"] += 1
        if is_gf: team_lb[t_a_name]["Grand Finals Won"] += 1
        for p in match["team_a"]: 
            ind_lb[p]["Wins"] += 1        
            if is_gf: ind_lb[p]["Grand Finals Won"] += 1
        for p in match["team_b"]:
            ind_lb[p]["Losses"] += 1
    else:                                                       
        team_lb[t_b_name]["Wins"] += 1                          
        team_lb[t_a_name]["Losses"] += 1
        if is_gf: team_lb[t_b_name]["Grand Finals Won"] += 1
        for p in match["team_b"]: 
            ind_lb[p]["Wins"] += 1        
            if is_gf: ind_lb[p]["Grand Finals Won"] += 1
        for p in match["team_a"]:
            ind_lb[p]["Losses"] += 1
            
    if "match_history" not in st.session_state.room_data:
        st.session_state.room_data["match_history"] = []
    
    logged_record = copy.deepcopy(match)
    logged_record["logged_at"] = str(datetime.datetime.now())
    st.session_state.room_data["match_history"].append(logged_record)
    
    if len(st.session_state.room_data["match_history"]) > 20:
        st.session_state.room_data["match_history"].pop(0)
        
    save_local_data(room_code, st.session_state.room_data)      

def undo_match_stats(match):
    ind_lb = st.session_state.room_data["ind_leaderboard"]
    team_lb = st.session_state.room_data["team_leaderboard"]
    
    t_a_name = " & ".join(sorted(match["team_a"]))               
    t_b_name = " & ".join(sorted(match["team_b"]))
    
    if t_a_name in team_lb: team_lb[t_a_name]["Points"] -= match["score_a"]
    if t_b_name in team_lb: team_lb[t_b_name]["Points"] -= match["score_b"]
    
    for p in match["team_a"]: 
        if p in ind_lb: ind_lb[p]["Points"] -= match["score_a"]
    for p in match["team_b"]: 
        if p in ind_lb: ind_lb[p]["Points"] -= match["score_b"]
        
    is_singles = len(match["team_a"]) == 1
    is_doubles = len(match["team_a"]) == 2
    is_gf = match.get("is_final", False) or "GRAND FINAL" in str(match.get("type", "")).upper()
    
    for p in match["team_a"] + match["team_b"]:
        if p in ind_lb:
            if is_singles: ind_lb[p]["Singles Played"] = max(0, ind_lb[p]["Singles Played"] - 1)
            elif is_doubles: ind_lb[p]["Doubles Played"] = max(0, ind_lb[p]["Doubles Played"] - 1)
            
    if match["score_a"] > match["score_b"]:                     
        if t_a_name in team_lb: 
            team_lb[t_a_name]["Wins"] = max(0, team_lb[t_a_name]["Wins"] - 1)
            if is_gf: team_lb[t_a_name]["Grand Finals Won"] = max(0, team_lb[t_a_name]["Grand Finals Won"] - 1)
        if t_b_name in team_lb: team_lb[t_b_name]["Losses"] = max(0, team_lb[t_b_name]["Losses"] - 1)
        for p in match["team_a"]: 
            if p in ind_lb: 
                ind_lb[p]["Wins"] = max(0, ind_lb[p]["Wins"] - 1)
                if is_gf: ind_lb[p]["Grand Finals Won"] = max(0, ind_lb[p]["Grand Finals Won"] - 1)
        for p in match["team_b"]:
            if p in ind_lb: ind_lb[p]["Losses"] = max(0, ind_lb[p]["Losses"] - 1)
    else:
        if t_b_name in team_lb: 
            team_lb[t_b_name]["Wins"] = max(0, team_lb[t_b_name]["Wins"] - 1)       
            if is_gf: team_lb[t_b_name]["Grand Finals Won"] = max(0, team_lb[t_b_name]["Grand Finals Won"] - 1)
        if t_a_name in team_lb: team_lb[t_a_name]["Losses"] = max(0, team_lb[t_a_name]["Losses"] - 1)
        for p in match["team_b"]: 
            if p in ind_lb:
                ind_lb[p]["Wins"] = max(0, ind_lb[p]["Wins"] - 1)       
                if is_gf: ind_lb[p]["Grand Finals Won"] = max(0, ind_lb[p]["Grand Finals Won"] - 1)
        for p in match["team_a"]:
            if p in ind_lb: ind_lb[p]["Losses"] = max(0, ind_lb[p]["Losses"] - 1)
            
    for current_m in st.session_state.room_data.get("matches", []):
        if current_m["id"] == match["id"]:
            current_m["logged"] = False
            if current_m["score_a"] >= current_m["max_points"] and current_m["score_a"] > current_m["score_b"]:
                current_m["score_a"] -= 1
            elif current_m["score_b"] >= current_m["max_points"] and current_m["score_b"] > current_m["score_a"]:
                current_m["score_b"] -= 1
            if current_m["score_a"] >= current_m["max_points"]: current_m["score_a"] = current_m["max_points"] - 1
            if current_m["score_b"] >= current_m["max_points"]: current_m["score_b"] = current_m["max_points"] - 1
            
    if "match_history" in st.session_state.room_data:
        st.session_state.room_data["match_history"] = [
            m for m in st.session_state.room_data["match_history"] if m["id"] != match["id"]
        ]
        
    save_local_data(room_code, st.session_state.room_data)

# ==============================================================================
# 🏆 SECTION 5: NAVIGATION WORKSPACE TABS (GLITCH-FREE CALL BACK STATE)
# ==============================================================================

tabs = [
    "👥 Roster & Expenses", 
    "🏆 Tournament Setup", 
    "⚡ Custom Match", 
    "🎮 Live Scoreboard", 
    "📈 Leaderboards"
] 

# Initialize base state values safely from query parameter defaults
if "active_tab" not in st.session_state:
    url_param = st.query_params.get("tab", tabs[0])
    st.session_state.active_tab = url_param if url_param in tabs else tabs[0]

# Callback event updates keys prior to running the template block logic
def run_tab_state_sync():
    st.query_params["tab"] = st.session_state.tab_selector
    st.session_state.active_tab = st.session_state.tab_selector

current_tab_index = tabs.index(st.session_state.active_tab)

selected_tab = st.radio(
    "Navigation Workspace:", 
    tabs, 
    index=current_tab_index, 
    horizontal=True, 
    key="tab_selector", 
    on_change=run_tab_state_sync
)

# ==============================================================================
# TAB 1: ROSTER & EXPENSES
# ==============================================================================
if selected_tab == "👥 Roster & Expenses":
    col_p, col_e = st.columns(2)                                
    
    with col_p:
        st.subheader("Player Management")
        new_player = st.text_input("Add Player Name:")          
        if st.button("Add Player", type="primary"):
            if new_player.strip() and new_player.strip() not in st.session_state.room_data["players"]:
                st.session_state.room_data["players"].append(new_player.strip()) 
                st.session_state.room_data["expenses"][new_player.strip()] = 0.0 
                save_local_data(room_code, st.session_state.room_data) 
                st.rerun()                                      
                
        st.markdown("#### Current Roster")
        for idx, player in enumerate(st.session_state.room_data["players"]):
            col_name, col_del = st.columns([5, 1])               
            col_name.write(f"• {player}")                        
            if col_del.button("🗑️", key=f"del_{player}_{idx}"):  
                st.session_state.room_data["players"].remove(player) 
                if player in st.session_state.room_data["expenses"]: del st.session_state.room_data["expenses"][player] 
                save_local_data(room_code, st.session_state.room_data) 
                st.rerun()

    with col_e:
        st.subheader("💰 Expense Ledger")
        for player in st.session_state.room_data["players"]:
            current_expense = st.session_state.room_data["expenses"].get(player, 0.0) 
            updated = st.number_input(f"{player} Paid ($):", min_value=0.0, value=float(current_expense), step=1.0, key=f"exp_{player}")
            if updated != current_expense:                      
                st.session_state.room_data["expenses"][player] = updated 
                save_local_data(room_code, st.session_state.room_data) 
        
        st.markdown("---")
        if st.session_state.room_data["expenses"] and st.button("🗑️ Reset Expense Ledger", type="secondary", use_container_width=True):
            for player in st.session_state.room_data["expenses"]: st.session_state.room_data["expenses"][player] = 0.0 
            save_local_data(room_code, st.session_state.room_data) 
            st.toast("💰 Expense records cleared back to $0.0!") 
            st.rerun()

# ==============================================================================
# TAB 2: TOURNAMENT SETUP
# ==============================================================================
elif selected_tab == "🏆 Tournament Setup":
    st.subheader("⚙️ Team Generation & Fixtures")
    
    st.markdown("#### 🎯 Today's Lineup")
    active_players = st.multiselect(
        "Select players playing this session:",
        options=st.session_state.room_data["players"],
        default=st.session_state.room_data["players"],
        help="Remove anyone who is absent so they aren't placed on a team."
    )

    match_type = st.radio("Format:", ["Singles", "Doubles"], index=1) 
    max_pts = st.number_input("Target Points (Qualifiers):", value=15, min_value=1) 
    final_pts = st.number_input("Target Points (Grand Final):", value=21, min_value=1) 
    
    col_btn1, col_btn2 = st.columns(2)                       
    with col_btn1:
        if st.button("👥 Lock Teams", use_container_width=True, type="secondary"):
            req = 2 if match_type == "Singles" else 4         
            if len(active_players) < req: 
                st.error(f"Need at least {req} active players for this format!")    
            else:
                generate_and_lock_teams(match_type, active_players)          
                st.rerun()
                
    with col_btn2:
        if st.button("🔓 Unlock & Re-roll", use_container_width=True): 
            req = 2 if match_type == "Singles" else 4
            if len(active_players) < req:
                st.error(f"Need at least {req} active players for this format!")
            else:
                generate_and_lock_teams(match_type, active_players)
                st.rerun()

    if st.session_state.room_data["teams"]:
        st.success("🔒 Teams Locked: " + " | ".join([" & ".join(t) for t in st.session_state.room_data["teams"]]))
    else:
        st.warning("⚠️ No fixed teams locked yet.")

    st.divider()
    num_teams = len(st.session_state.room_data["teams"])    
    m_count = st.number_input("Number of Matches to Draw:", min_value=1, value=max(1, num_teams)) 

    if st.button("🎲 Draw Random Matches", use_container_width=True):
        if len(st.session_state.room_data["teams"]) < 2:
            st.error("Need at least 2 locked teams!")
        else:
            valid_draw_pairs = []
            for team_a, team_b in itertools.combinations(st.session_state.room_data["teams"], 2):
                if set(team_a).isdisjoint(set(team_b)):
                    valid_draw_pairs.append((team_a, team_b))
            
            if not valid_draw_pairs:
                st.error("❌ Not enough non-overlapping team setups to generate a match.")
            else:
                random.shuffle(valid_draw_pairs)                        
                fixtures = []                                    
                for i in range(int(m_count)):
                    pair = valid_draw_pairs[i % len(valid_draw_pairs)]      
                    fixtures.append({
                        "id": str(uuid.uuid4()), "type": "Round Match", "is_final": False, "logged": False,                         
                        "team_a": pair[0], "team_b": pair[1], "score_a": 0, "score_b": 0, "max_points": int(max_pts)               
                    })
                st.session_state.room_data["matches"] = fixtures 
                save_local_data(room_code, st.session_state.room_data)
                
                st.session_state.active_tab = "🎮 Live Scoreboard"
                st.query_params["tab"] = "🎮 Live Scoreboard"
                st.rerun()

    if st.button("🏆 Start Tournament Pack", use_container_width=True, type="primary"):
        if len(st.session_state.room_data["teams"]) < 2:
            st.error("Need at least 2 locked teams!")
        else:
            valid_draw_pairs = []
            for team_a, team_b in itertools.combinations(st.session_state.room_data["teams"], 2):
                if set(team_a).isdisjoint(set(team_b)):
                    valid_draw_pairs.append((team_a, team_b))

            if not valid_draw_pairs:
                st.error("❌ Not enough non-overlapping team setups to generate a match.")
            else:
                random.shuffle(valid_draw_pairs)
                fixtures = []
                for i in range(int(m_count)):
                    pair = valid_draw_pairs[i % len(valid_draw_pairs)]
                    fixtures.append({
                        "id": str(uuid.uuid4()), "type": f"Qualifier #{i+1}", "is_final": False, "logged": False,
                        "team_a": pair[0], "team_b": pair[1], "score_a": 0, "score_b": 0, "max_points": int(max_pts)
                    })
                fixtures.append({
                    "id": str(uuid.uuid4()), "type": "GRAND FINAL", "is_final": True, "logged": False,
                    "team_a": ["TBD"], "team_b": ["TBD"], "score_a": 0, "score_b": 0, "max_points": int(final_pts) 
                })
                st.session_state.room_data["matches"] = fixtures
                save_local_data(room_code, st.session_state.room_data)
                
                st.session_state.active_tab = "🎮 Live Scoreboard"
                st.query_params["tab"] = "🎮 Live Scoreboard"
                st.rerun()

# ==============================================================================
# TAB 3: QUICK CUSTOM MATCH
# ==============================================================================
elif selected_tab == "⚡ Custom Match":
    st.subheader("⚡ Quick Custom Match Generator")
    st.write("Manually select players for a one-off custom match. This instantly adds the match to the Live Scoreboard.")
    
    q_format = st.radio("Match Format:", ["Singles", "Doubles"], index=1, key="q_format", horizontal=True)
    req_players = 1 if q_format == "Singles" else 2
    
    all_players = st.session_state.room_data["players"]
    current_team_a = st.session_state.get("q_team_a", [])
    current_team_b = st.session_state.get("q_team_b", [])
    
    options_for_a = [p for p in all_players if p not in current_team_b]
    options_for_b = [p for p in all_players if p not in current_team_a]
    
    col_qa, col_qb = st.columns(2)
    with col_qa:
        st.markdown("### Team A")
        q_team_a = st.multiselect(f"Select {req_players} Player(s):", options=options_for_a, max_selections=req_players, key="q_team_a")
            
    with col_qb:
        st.markdown("### Team B")
        q_team_b = st.multiselect(f"Select {req_players} Player(s):", options=options_for_b, max_selections=req_players, key="q_team_b")
            
    q_pts = st.number_input("Target Points (Race to):", value=21, min_value=1, key="q_pts")
    
    if st.button("⚔️ Generate Custom Match & Go to Scoreboard", type="primary", use_container_width=True):
        if len(q_team_a) != req_players or len(q_team_b) != req_players:
            st.error(f"Please select exactly {req_players} player(s) for each team before generating!")
        else:
            new_match = {
                "id": str(uuid.uuid4()), "type": "Custom Match", "is_final": False, "logged": False,
                "team_a": q_team_a, "team_b": q_team_b, "score_a": 0, "score_b": 0, "max_points": int(q_pts)
            }
            st.session_state.room_data["matches"].append(new_match)
            save_local_data(room_code, st.session_state.room_data)
            
            st.session_state.active_tab = "🎮 Live Scoreboard"
            st.query_params["tab"] = "🎮 Live Scoreboard"
            st.rerun()

# ==============================================================================
# TAB 4: LIVE SCOREBOARD
# ==============================================================================
elif selected_tab == "🎮 Live Scoreboard":
    st.subheader("🔴 Live Scoreboard")
    
    if not st.session_state.room_data["matches"]:
        st.info("No active matches. Go to **Tournament Setup** or **Custom Match** to generate fixtures!")
    else:
        if st.button("🗑️ Clear All Current Fixtures", type="secondary"):
            st.session_state.room_data["matches"] = []          
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()
            
        current_pack_stats = {}
        for t in st.session_state.room_data["teams"]:
            t_key = " & ".join(t)
            current_pack_stats[t_key] = {"Wins": 0, "Points": 0, "TeamRaw": t} 

        for match in st.session_state.room_data["matches"]:
            if not match.get("is_final", False) and (match["score_a"] >= match["max_points"] or match["score_b"] >= match["max_points"]):
                t_a_str = " & ".join(match["team_a"])
                t_b_str = " & ".join(match["team_b"])
                
                if t_a_str not in current_pack_stats: current_pack_stats[t_a_str] = {"Wins": 0, "Points": 0, "TeamRaw": match["team_a"]}
                if t_b_str not in current_pack_stats: current_pack_stats[t_b_str] = {"Wins": 0, "Points": 0, "TeamRaw": match["team_b"]}
                
                current_pack_stats[t_a_str]["Points"] += match["score_a"] 
                current_pack_stats[t_b_str]["Points"] += match["score_b"] 
                
                if match["score_a"] > match["score_b"]: current_pack_stats[t_a_str]["Wins"] += 1     
                else: current_pack_stats[t_b_str]["Wins"] += 1     

        sorted_pack_teams = sorted(current_pack_stats.values(), key=lambda x: (x["Wins"], x["Points"]), reverse=True)

        for idx, match in enumerate(st.session_state.room_data["matches"]):
            if match.get("is_final", False):                     
                st.markdown(f"### 🏆 GRAND FINAL — Race to {match['max_points']}")
                if len(sorted_pack_teams) >= 2:                  
                    match["team_a"] = sorted_pack_teams[0]["TeamRaw"] 
                    match["team_b"] = sorted_pack_teams[1]["TeamRaw"] 
            else:
                st.markdown(f"**Match #{idx + 1} ({match['type']})**") 
                
            col_t1, col_s1, col_vs, col_s2, col_t2 = st.columns([3, 1, 1, 1, 3]) 
            
            with col_t1: st.write(f"**{' & '.join(match['team_a'])}**") 
            
            with col_s1: 
                score_a = st.number_input("Team A", min_value=0, value=match["score_a"], key=f"a_{match['id']}", label_visibility="collapsed")
                if score_a != match["score_a"]:                  
                    match["score_a"] = score_a                   
                    save_local_data(room_code, st.session_state.room_data) 
            
            with col_vs: st.write("VS")
            
            with col_s2: 
                score_b = st.number_input("Team B", min_value=0, value=match["score_b"], key=f"b_{match['id']}", label_visibility="collapsed")
                if score_b != match["score_b"]:
                    match["score_b"] = score_b
                    save_local_data(room_code, st.session_state.room_data)
            
            with col_t2: st.write(f"**{' & '.join(match['team_b'])}**")
            
            if match["score_a"] >= match["max_points"] or match["score_b"] >= match["max_points"]:
                winner_name = ' & '.join(match['team_a']) if match["score_a"] > match["score_b"] else ' & '.join(match['team_b'])
                
                if not match.get("logged", False):               
                    match["logged"] = True                       
                    log_match_to_history(match)                  
                    st.rerun()                                   
                
                if match.get("is_final", False):                 
                    st.balloons()                                
                    st.success(f"👑 {winner_name} WINS THE TOURNAMENT CHAMPIONSHIP! 👑") 
                else:
                    st.success(f"✅ **{winner_name}** won the match! (Stats saved to Leaderboard)")
            st.divider()

    st.markdown("---")
    st.subheader("⏪ Recent Match History")
    
    match_history = st.session_state.room_data.get("match_history", [])
    if not match_history:
        st.info("No matches have been finished recently.")
    else:
        for m in reversed(match_history[-10:]):
            t_a = " & ".join(m["team_a"])
            t_b = " & ".join(m["team_b"])
            winner = t_a if m["score_a"] > m["score_b"] else t_b
            
            col_info, col_btn = st.columns([5, 1])
            with col_info:
                st.write(f"**{m['type']}**: {t_a} ({m['score_a']}) vs {t_b} ({m['score_b']}) — *Won by {winner}*")
            with col_btn:
                if st.button("↩️ Undo", key=f"undo_{m['id']}"):
                    undo_match_stats(m)
                    st.toast(f"Match between {t_a} and {t_b} successfully undone!")
                    st.rerun()

# ==============================================================================
# TAB 5: LEADERBOARDS
# ==============================================================================
elif selected_tab == "📈 Leaderboards":
    st.subheader("📈 All-Time Standings")
    
    ind_stats = st.session_state.room_data["ind_leaderboard"]    
    team_stats = st.session_state.room_data["team_leaderboard"]   
    
    col_l1, col_l2 = st.columns(2)                                
    with col_l1:
        st.markdown("### 🥇 Individual Leaderboard")
        all_tracked_players = set(st.session_state.room_data.get("players", [])) | set(ind_stats.keys())
        
        display_profiles = {}
        for player in all_tracked_players:
            saved_profile = ind_stats.get(player, {})
            display_profiles[player] = {
                "Wins": saved_profile.get("Wins", 0), 
                "Losses": saved_profile.get("Losses", 0), 
                "Singles Played": saved_profile.get("Singles Played", 0),
                "Doubles Played": saved_profile.get("Doubles Played", 0), 
                "Grand Finals Won": saved_profile.get("Grand Finals Won", 0),
                "Total Points": saved_profile.get("Points", 0)
            }
            
        if display_profiles:     
            df_ind = pd.DataFrame.from_dict(display_profiles, orient='index').sort_values(by=["Grand Finals Won", "Wins", "Total Points"], ascending=[False, False, False])
            st.dataframe(df_ind, use_container_width=True)       
        else: st.info("No stats available.")
            
    with col_l2:
        st.markdown("### 🏅 Team Leaderboard")
        if team_stats:
            for t_name in team_stats:
                if "Losses" not in team_stats[t_name]: team_stats[t_name]["Losses"] = 0
                if "Grand Finals Won" not in team_stats[t_name]: team_stats[t_name]["Grand Finals Won"] = 0
                
            df_team = pd.DataFrame.from_dict(team_stats, orient='index').sort_values(by=["Grand Finals Won", "Wins", "Points"], ascending=[False, False, False])
            if not df_team.empty: df_team = df_team[["Grand Finals Won", "Wins", "Losses", "Points"]]
            st.dataframe(df_team, use_container_width=True)
        else: st.info("No stats available.")

    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("⚠️ Hard Reset Leaderboards", use_container_width=True, type="secondary"):
            st.session_state.room_data["ind_leaderboard"] = {}   
            st.session_state.room_data["team_leaderboard"] = {}  
            st.session_state.room_data["match_history"] = [] 
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()
    with col_r2:
        if st.button("🔄 Dissolve Fixed Teams List", use_container_width=True):
            st.session_state.room_data["teams"] = []             
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()