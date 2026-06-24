# ==============================================================================
# 🏸 BADMINTON CLUBHOUSE LOCAL ENGINE - COMPLETE ARCHITECTURE WITH ODD-PLAYER LOGIC
# ==============================================================================

# --- DEPENDENCY REGISTRATION ---
import streamlit as st  
import random           
import uuid             
import pandas as pd     
import itertools        
import datetime         
import shelve           

# --- GLOBAL STAGE INITIALIZATION ---
st.set_page_config(
    page_title="Badminton Clubhouse Local",  
    page_icon="🏸🏸",                          
    layout="wide",                           
    initial_sidebar_state="collapsed"        
)

DB_FILE = "badminton_clubhouse_db"

# ==============================================================================
# 💾 SECTION 1: PERSISTENT STORAGE MANAGEMENT FUNCTIONS
# ==============================================================================

def get_local_data(room_name):
    with shelve.open(DB_FILE) as db:
        if room_name not in db:
            default_data = {
                "players": [],              
                "teams": [],                
                "matches": [],              
                "expenses": {},             
                "ind_leaderboard": {},      
                "team_leaderboard": {},     
                "created_at": str(datetime.date.today()), 
                "total_visits": 1           
            }
            db[room_name] = default_data    
            return default_data             
        
        data = db[room_name]                
        if "total_visits" not in data: data["total_visits"] = 0        
        data["total_visits"] += 1           
        
        updated = False                     
        for key, default_val in [
            ("players", []), ("teams", []), ("matches", []), 
            ("expenses", {}), ("ind_leaderboard", {}), ("team_leaderboard", {}),
            ("created_at", str(datetime.date.today()))
        ]:
            if key not in data:             
                data[key] = default_val     
                updated = True              
                
        if updated: db[room_name] = data            
        return data                         

def save_local_data(room_name, data):
    with shelve.open(DB_FILE) as db:        
        db[room_name] = data                

# ==============================================================================
# 🔑 SECTION 2: ACCESS CONTROL GATEWAY INTERFACE
# ==============================================================================

if "room_id" not in st.session_state:
    st.title("🏸 Badminton Clubhouse Portal (Local Mode)") 
    room_input = st.text_input("Group Access Code (e.g., SUNDAY-SMASH)", "").strip().upper()
    
    if st.button("Enter Dashboard", type="primary"): 
        if room_input == "ADMIN-STATS":              
            st.session_state.room_id = "ADMIN_PANEL" 
            st.rerun()                               
        elif room_input:                             
            st.session_state.room_id = room_input    
            st.rerun()                               
    st.stop()                                        

room_code = st.session_state.room_id

if "room_data" not in st.session_state and room_code != "ADMIN_PANEL":
    st.session_state.room_data = get_local_data(room_code) 

# ==============================================================================
# 🛡️ SECTION 3: SYSTEM AUDIT INSIGHTS (BACKDOOR ADMINISTRATIVE COMPONENT)
# ==============================================================================

if st.session_state.room_id == "ADMIN_PANEL":
    st.title("🛡️ Central System Analytics (Local Database)")
    st.subheader("File Footprint & Room Traffic Monitor")
    
    if st.button("⬅️ Log Out of Admin Mode", type="primary"): 
        del st.session_state.room_id                        
        st.rerun()                                          
        
    st.markdown("---")                                      
    admin_summary_data = []                                 
    
    with shelve.open(DB_FILE) as db:                        
        for r_id in db.keys():                              
            room_payload = db[r_id]                         
            created_date = room_payload.get("created_at", "Legacy Engine Record") 
            traffic_hits = room_payload.get("total_visits", 1) 
            registered_players = len(room_payload.get("players", [])) 
            active_matches = len(room_payload.get("matches", [])) 
            
            admin_summary_data.append({
                "Room Access Code": r_id, "Creation Date": created_date,
                "Total Dashboard Openings": traffic_hits, "Registered Players": registered_players,
                "Active Brackets": active_matches
            })
        
    st.metric(label="Total Created Activity Rooms", value=len(admin_summary_data))
    st.markdown("### 📋 Active Storage Register")
        
    if admin_summary_data:                                  
        df_admin = pd.DataFrame(admin_summary_data)         
        st.dataframe(df_admin, use_container_width=True)    
        
        csv = df_admin.to_csv(index=False).encode('utf-8')  
        st.download_button(label="📥 Download Database Metadata CSV Report", data=csv, file_name="audit.csv", mime="text/csv")
    else:
        st.info("System storage arrays are completely blank right now.") 
    st.stop()                                               

# ==============================================================================
# 🗂️ SECTION 4: MAIN DASHBOARD LAYOUT & CORE BRACKET CALCULATIONS
# ==============================================================================

col1, col2 = st.columns([4, 1])                             
with col1:
    st.title(f"🏸 Match & Tournament Hub")
    st.caption(f"Active Local Room: **{room_code}**")      
with col2:
    if st.button("Change Room / Exit", use_container_width=True): 
        del st.session_state.room_id                        
        if "room_data" in st.session_state: del st.session_state.room_data                  
        st.rerun()

st.markdown("---")

def generate_and_lock_teams(match_format):
    """
    Core Matchmaking Logic updated with ODD-PLAYER generation matrix.
    If 5 players are present, teams are formed for 4, and the 5th creates a team with everyone else.
    """
    master_player_list = list(st.session_state.room_data["players"]) 
    shuffled_pool = list(master_player_list)                               
    random.shuffle(shuffled_pool)                               
    st.session_state.room_data["teams"] = []                    
    
    if match_format == "Singles":                               
        for p in shuffled_pool:                                 
            st.session_state.room_data["teams"].append([p])     
    else:                                                       
        # 1. Generate standard non-overlapping doubles teams
        while len(shuffled_pool) >= 2:                          
            st.session_state.room_data["teams"].append([shuffled_pool.pop(), shuffled_pool.pop()]) 
            
        # 2. Odd-Player Generation Logic Trigger
        if len(shuffled_pool) == 1:
            odd_player = shuffled_pool.pop()
            # Loop through the original complete roster
            for other_player in master_player_list:
                # Pair the odd player with everyone else (as long as it's not themselves)
                if other_player != odd_player:
                    st.session_state.room_data["teams"].append([odd_player, other_player])
            
    save_local_data(room_code, st.session_state.room_data)      

def log_match_to_history(match):
    ind_lb = st.session_state.room_data["ind_leaderboard"]      
    team_lb = st.session_state.room_data["team_leaderboard"]    
    
    t_a_name = " & ".join(sorted(match["team_a"]))               
    t_b_name = " & ".join(sorted(match["team_b"]))               
    
    if t_a_name not in team_lb: team_lb[t_a_name] = {"Wins": 0, "Points": 0}
    if t_b_name not in team_lb: team_lb[t_b_name] = {"Wins": 0, "Points": 0}
        
    for p in match["team_a"] + match["team_b"]:
        if p not in ind_lb:
            ind_lb[p] = {"Wins": 0, "Points": 0, "Singles Played": 0, "Doubles Played": 0, "Grand Finals Won": 0}
        if "Singles Played" not in ind_lb[p]: ind_lb[p]["Singles Played"] = 0
        if "Doubles Played" not in ind_lb[p]: ind_lb[p]["Doubles Played"] = 0
        if "Grand Finals Won" not in ind_lb[p]: ind_lb[p]["Grand Finals Won"] = 0
        
    team_lb[t_a_name]["Points"] += match["score_a"]             
    team_lb[t_b_name]["Points"] += match["score_b"]             
    
    for p in match["team_a"]: ind_lb[p]["Points"] += match["score_a"] 
    for p in match["team_b"]: ind_lb[p]["Points"] += match["score_b"] 
    
    is_singles_match = len(match["team_a"]) == 1
    is_doubles_match = len(match["team_a"]) == 2
    is_gf = match.get("is_final", False) or "GRAND FINAL" in str(match.get("type", "")).upper()
    
    for p in match["team_a"] + match["team_b"]:
        if is_singles_match: ind_lb[p]["Singles Played"] += 1
        elif is_doubles_match: ind_lb[p]["Doubles Played"] += 1

    if match["score_a"] > match["score_b"]:                     
        team_lb[t_a_name]["Wins"] += 1                          
        for p in match["team_a"]: 
            ind_lb[p]["Wins"] += 1        
            if is_gf: ind_lb[p]["Grand Finals Won"] += 1
    else:                                                       
        team_lb[t_b_name]["Wins"] += 1                          
        for p in match["team_b"]: 
            ind_lb[p]["Wins"] += 1        
            if is_gf: ind_lb[p]["Grand Finals Won"] += 1
        
    save_local_data(room_code, st.session_state.room_data)      

# ==============================================================================
# 🏆 SECTION 5: SYSTEM APPLICATION VIEWSPACE NAVIGATION TAB BAR
# ==============================================================================

tabs = ["👥 Roster & Expenses", "🎮 Matches & Play", "🏆 Leaderboards"] 
selected_tab = st.radio("Navigation Workspace:", tabs, horizontal=True, key="tab_navigation") 

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

elif selected_tab == "🎮 Matches & Play":
    col_cfg, col_play = st.columns([1, 2])                      
    
    with col_cfg:
        st.subheader("⚙️ Team Generation & Fixtures")
        # 🔥 FIX: Added index=1 so "Doubles" is ticked by default when the user loads the screen.
        match_type = st.radio("Format:", ["Singles", "Doubles"], index=1) 
        max_pts = st.number_input("Target Points (Qualifiers/Regular):", value=21, min_value=1) 
        final_pts = st.number_input("Target Points (Grand Final Only):", value=21, min_value=1) 
        
        col_btn1, col_btn2 = st.columns(2)                       
        with col_btn1:
            if st.button("👥 Lock Teams", use_container_width=True, type="secondary"):
                req = 2 if match_type == "Singles" else 4         
                if len(st.session_state.room_data["players"]) < req: 
                    st.error(f"Need at least {req} players for this format!")    
                else:
                    generate_and_lock_teams(match_type)          
                    st.rerun()
                    
        with col_btn2:
            if st.button("🔓 Unlock & Re-roll", use_container_width=True): 
                req = 2 if match_type == "Singles" else 4
                if len(st.session_state.room_data["players"]) < req:
                    st.error(f"Need at least {req} players for this format!")
                else:
                    generate_and_lock_teams(match_type)
                    st.rerun()

        if st.session_state.room_data["teams"]:
            st.info("🔒 Teams: " + " | ".join([" & ".join(t) for t in st.session_state.room_data["teams"]]))
        else:
            st.warning("⚠️ No fixed teams locked yet.")

        st.divider()

        num_teams = len(st.session_state.room_data["teams"])    
        m_count = st.number_input("Number of Matches to Draw:", min_value=1, value=max(1, num_teams)) 

        # --- MATCH SCHEDULING SIMULATION ENGINE ---
        if num_teams >= 2:
            # Generate mathematically valid pairings (Ensuring no player plays against themselves)
            valid_sim_pairings = []
            for i, j in itertools.combinations(range(num_teams), 2):
                team_a_roster = set(st.session_state.room_data["teams"][i])
                team_b_roster = set(st.session_state.room_data["teams"][j])
                
                # Check for physical reality: A player cannot exist on both sides of the net
                if team_a_roster.isdisjoint(team_b_roster):
                    valid_sim_pairings.append((i, j))
            
            if valid_sim_pairings:
                simulated_counts = {i: 0 for i in range(num_teams)} 
                
                for i in range(int(m_count)):
                    pair = valid_sim_pairings[i % len(valid_sim_pairings)]       
                    simulated_counts[pair[0]] += 1                   
                    simulated_counts[pair[1]] += 1                   
                    
                unique_match_frequencies = set(simulated_counts.values()) 
                if len(unique_match_frequencies) <= 1:              
                    st.success("💪 Perfect Balance! All distinct teams play an identical number of matches.")
                else:                                               
                    max_m = max(simulated_counts.values())          
                    shortchanged_teams = [" & ".join(st.session_state.room_data["teams"][t_idx]) for t_idx, count in simulated_counts.items() if count < max_m]
                    st.warning(f"⚠️ **Uneven Play Warning:** Some pairings appear fewer times:\n" + "\n".join([f"- {t}" for t in shortchanged_teams]))
            else:
                st.error("⚠️ Cannot form valid non-overlapping matches with the current teams.")

        # --- FIXTURES DRAW TRIGGER ACTIONS ---
        if st.button("🎲 Draw Random Matches", use_container_width=True):
            if len(st.session_state.room_data["teams"]) < 2:
                st.error("Need at least 2 locked teams!")
            else:
                # 🛡️ PHYSICAL REALITY FILTER FOR DRAW GENERATION
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
                    st.rerun()

        # ==============================================================================
        # 🔄 DYNAMIC MID-TOURNAMENT SUBSTITUTION SYSTEM
        # ==============================================================================
        if st.session_state.room_data["matches"]:                  
            upcoming_fixtures = [(idx, m) for idx, m in enumerate(st.session_state.room_data["matches"]) if not m.get("logged", False)]
            
            if upcoming_fixtures:                               
                st.divider()                                    
                st.subheader("🔄 Dynamic Mid-Tournament Sub")  
                match_options = {f"Match #{idx + 1} ({m['type']})": (idx, m) for idx, m in upcoming_fixtures}
                selected_match_label = st.selectbox("Target Upcoming Match:", list(match_options.keys())) 
                target_idx, target_match = match_options[selected_match_label] 
                
                on_court_players = sorted(list(set(target_match["team_a"] + target_match["team_b"])))
                on_court_players = [p for p in on_court_players if p != "TBD"] 
                
                if on_court_players:                             
                    player_leaving = st.selectbox("Player Stepping Down:", on_court_players, key="sub_leave_select")
                    available_subs = sorted([p for p in st.session_state.room_data["players"] if p not in on_court_players])
                    sub_source = st.radio("Replacement Entry:", ["Select Available Active Player", "Register New Player"], horizontal=True)
                    player_entering = ""                         
                    
                    if sub_source == "Select Available Active Player": 
                        if available_subs: player_entering = st.selectbox("Available Players:", available_subs, key="sub_active_select") 
                    else:
                        player_entering = st.text_input("Type New Player Name:", key="sub_enter_input").strip() 
                    
                    if st.button("Apply Match Substitution", use_container_width=True, type="secondary"): 
                        if player_entering:                      
                            target_leaving = player_leaving.strip().lower()
                            target_entering = player_entering.strip() 
                            swap_occurred = False                
                            matches_updated_count = 0            
                            
                            if target_entering not in st.session_state.room_data["players"]:
                                st.session_state.room_data["players"].append(target_entering) 
                                st.session_state.room_data["expenses"][target_entering] = 0.0 
                            
                            for idx in range(target_idx, len(st.session_state.room_data["matches"])):
                                current_m = st.session_state.room_data["matches"][idx] 
                                if not current_m.get("logged", False): 
                                    old_team_a = list(current_m["team_a"])
                                    old_team_b = list(current_m["team_b"])
                                    
                                    current_m["team_a"] = [target_entering if p.strip().lower() == target_leaving else p for p in current_m["team_a"]]
                                    current_m["team_b"] = [target_entering if p.strip().lower() == target_leaving else p for p in current_m["team_b"]]
                                    
                                    if current_m["team_a"] != old_team_a or current_m["team_b"] != old_team_b:
                                        swap_occurred = True     
                                        matches_updated_count += 1 
                            
                            for t_idx, team in enumerate(st.session_state.room_data["teams"]):
                                st.session_state.room_data["teams"][t_idx] = [target_entering if p.strip().lower() == target_leaving else p for p in team]
                            
                            if not swap_occurred: st.error(f"❌ Swap Failed: No match files matched '{player_leaving}'.")
                            else:                                
                                save_local_data(room_code, st.session_state.room_data) 
                                st.toast(f"🔄 Swapped {player_leaving} with {target_entering} across {matches_updated_count} upcoming matches!") 
                                st.rerun()                       
                        else: st.error("Please pick or type a valid replacement.")

    # ==============================================================================
    # 🎮 TAB WORKSPACE MODULE 2 (RIGHT COMPONENT): LIVE SCOREBOARD INTERFACE
    # ==============================================================================
    with col_play:
        st.subheader("Live Scoreboard")
        if st.session_state.room_data["matches"] and st.button("🗑️ Clear Current Fixtures"):
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
                if not match.get("logged", False):               
                    match["logged"] = True                       
                    log_match_to_history(match)                  
                    st.rerun()                                   
                
                if match.get("is_final", False):                 
                    champ = ' & '.join(match['team_a']) if match['score_a'] > match['score_b'] else ' & '.join(match['team_b'])
                    st.balloons()                                
                    st.success(f"👑 {champ} WINS THE TOURNAMENT CHAMPIONSHIP! 👑") 
                else:
                    st.success("✅ Saved to Leaderboard!")
            st.divider()                                         

# ==============================================================================
# 🏆 TAB WORKSPACE MODULE 3: LEADERBOARDS
# ==============================================================================
elif selected_tab == "🏆 Leaderboards":
    st.subheader("📈 All-Time Standings")
    ind_stats = st.session_state.room_data["ind_leaderboard"]    
    team_stats = st.session_state.room_data["team_leaderboard"]   
    
    col_l1, col_l2 = st.columns(2)                                
    with col_l1:
        st.markdown("### 🥇 Individual Leaderboard")
        display_profiles = {}
        for player in st.session_state.room_data.get("players", []):
            saved_profile = ind_stats.get(player, {})
            display_profiles[player] = {
                "Wins": saved_profile.get("Wins", 0), "Singles Played": saved_profile.get("Singles Played", 0),
                "Doubles Played": saved_profile.get("Doubles Played", 0), "Grand Finals Won": saved_profile.get("Grand Finals Won", 0),
                "Total points scored": saved_profile.get("Points", 0)
            }
            
        if display_profiles:                                            
            df_ind = pd.DataFrame.from_dict(display_profiles, orient='index').sort_values(by=["Grand Finals Won", "Wins", "Total points scored"], ascending=[False, False, False])
            st.dataframe(df_ind, use_container_width=True)       
        else: st.info("No stats available.")
            
    with col_l2:
        st.markdown("### 🏅 Team Leaderboard")
        if team_stats:
            df_team = pd.DataFrame.from_dict(team_stats, orient='index').sort_values(by=["Wins", "Points"], ascending=[False, False])
            st.dataframe(df_team, use_container_width=True)
        else: st.info("No stats available.")

    st.markdown("---")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("⚠️ Hard Reset Leaderboards", use_container_width=True, type="secondary"):
            st.session_state.room_data["ind_leaderboard"] = {}   
            st.session_state.room_data["team_leaderboard"] = {}  
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()
    with col_r2:
        if st.button("🔄 Dissolve Fixed Teams List", use_container_width=True):
            st.session_state.room_data["teams"] = []             
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()