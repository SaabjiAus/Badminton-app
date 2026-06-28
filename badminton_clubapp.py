# ==============================================================================
# 🏸 BADMINTON CLUBHOUSE - STREAMLIT CLOUD + SUPABASE PRODUCTION ENGINE
# ==============================================================================

# --- IMPORTING REQUIRED LIBRARIES ---
import streamlit as st      # The core framework used to build the web app interface
import random               # Used to shuffle players randomly when making teams
import uuid                 # Generates unique tracking IDs for each match to prevent score overlap
import pandas as pd         # Converts your data into clean, sortable tables (DataFrames)
import itertools            # Used specifically to calculate all possible team matchups
import datetime             # Used to log the date when a new room is created
from supabase import create_client, Client  # Tools used to connect to your Supabase cloud database

# --- GLOBAL STAGE INITIALIZATION ---
# Sets up the basic look and behavior of the web browser tab
st.set_page_config(
    page_title="Badminton Clubhouse Cloud",  # The text that appears on the browser tab
    page_icon="🏸",                          # The emoji icon on the browser tab
    layout="wide",                           # Stretches the app to fill the whole screen width
    initial_sidebar_state="collapsed"        # Hides Streamlit's default left-hand sidebar
)

# ==============================================================================
# 💾 SECTION 1: SUPABASE LIVE CLOUD STORAGE MANAGEMENT FUNCTIONS
# ==============================================================================

# Pulling secret database credentials securely from Streamlit Cloud's settings
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Creating the active connection "bridge" to your Supabase database
supabase_client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_local_data(room_name):
    # PURPOSE: Fetches the data for a specific group (room_name) from the cloud.
    # If the group doesn't exist yet, it creates a blank starting template for them.
    try:
        # Search the 'clubhouse_rooms' table for the specific room code
        response = supabase_client.table("clubhouse_rooms").select("room_data").eq("room_id", room_name).execute()
        
        # If the room exists and returns data:
        if response.data:
            data = response.data[0]["room_data"] # Extract the actual dictionary of stats/players
            
            # Track how many times this room has been logged into
            if "total_visits" not in data: data["total_visits"] = 0        
            data["total_visits"] += 1           
            
            updated = False # A flag to check if we need to save missing keys
            
            # This loop automatically updates older rooms with new features.
            # If we add a new feature (like "team_leaderboard"), this makes sure older rooms get an empty one instead of crashing.
            for key, default_val in [
                ("players", []), ("teams", []), ("matches", []), 
                ("expenses", {}), ("ind_leaderboard", {}), ("team_leaderboard", {}),
                ("created_at", str(datetime.date.today()))
            ]:
                if key not in data:             
                    data[key] = default_val     
                    updated = True              
            
            # If we had to add missing keys or update visits, save it back to the cloud
            if updated: save_local_data(room_name, data)            
            return data # Return the final, clean data dictionary to the app
        
        # If the room DOES NOT exist, create a brand new dictionary structure for it
        default_data = {
            "players": [], "teams": [], "matches": [], "expenses": {},             
            "ind_leaderboard": {}, "team_leaderboard": {},     
            "created_at": str(datetime.date.today()), "total_visits": 1           
        }
        # Insert this brand new room into the Supabase database
        supabase_client.table("clubhouse_rooms").insert({"room_id": room_name, "room_data": default_data}).execute()
        return default_data
        
    except Exception as e:
        # If the internet drops or Supabase crashes, show an error and return empty data
        st.error(f"🚨 Supabase Fetch Failure: {e}")
        return {"players": [], "teams": [], "matches": [], "expenses": {}, "ind_leaderboard": {}, "team_leaderboard": {}}

def save_local_data(room_name, data):
    # PURPOSE: Pushes updated data (new scores, new players) back up to the cloud.
    try:
        # Update the row where the room_id matches, replacing old data with the new data
        supabase_client.table("clubhouse_rooms").update({"room_data": data, "updated_at": "now()"}).eq("room_id", room_name).execute()
    except Exception as e:
        st.error(f"🚨 Supabase Update Sync Failure: {e}")

# ==============================================================================
# 🔑 SECTION 2: ACCESS CONTROL GATEWAY INTERFACE (STICKY URLs)
# ==============================================================================

# If the user hasn't logged in yet (room_id is missing from temporary memory)
if "room_id" not in st.session_state:
    # Check if the URL already has a saved room (e.g., website.com/?room=SMASH)
    if "room" in st.query_params:
        st.session_state.room_id = st.query_params["room"] # Log them in automatically
    else:
        # Otherwise, show the login screen
        st.title("🏸 Badminton Clubhouse Portal (Cloud Mode)") 
        
        # Text box for typing the access code (forces uppercase and removes extra spaces)
        room_input = st.text_input("Group Access Code (e.g., SUNDAY-SMASH)", "").strip().upper()
        
        if st.button("Enter Dashboard", type="primary"): 
            if room_input == "ADMIN-STATS":              
                st.session_state.room_id = "ADMIN_PANEL" # Special admin mode
                st.query_params["room"] = "ADMIN_PANEL"  # Save admin mode to URL
                st.rerun() # Refresh app to apply login                               
            elif room_input:                             
                st.session_state.room_id = room_input    # Standard room login
                st.query_params["room"] = room_input     # Save room to URL so it survives refreshes
                st.rerun()                               
        st.stop() # Stops the rest of the code from running until they log in                                       

# A shortcut variable holding the current active room name
room_code = st.session_state.room_id

# If we are logged in, but haven't downloaded the room's data yet, fetch it now.
if "room_data" not in st.session_state and room_code != "ADMIN_PANEL":
    st.session_state.room_data = get_local_data(room_code) 

# ==============================================================================
# 🛡️ SECTION 3: SYSTEM AUDIT INSIGHTS (ADMIN PANEL)
# ==============================================================================

# If the user typed the special admin code, show this dashboard instead of the normal app
if st.session_state.room_id == "ADMIN_PANEL":
    st.title("🛡️ Central Cloud Analytics Controls")
    
    # Logout button logic for admin
    if st.button("⬅️ Log Out of Admin Mode", type="primary"): 
        del st.session_state.room_id                        
        if "room" in st.query_params: del st.query_params["room"]
        if "tab" in st.query_params: del st.query_params["tab"]
        st.rerun()                                          
        
    st.markdown("---")                                      
    
    # List to collect summary details of all rooms
    admin_summary_data = []                                 
    
    try:
        # Ask Supabase for every single room in the database
        response = supabase_client.table("clubhouse_rooms").select("room_id", "room_data").execute()
        if response.data:
            # Loop through each room and extract key stats
            for row in response.data:                              
                r_id = row["room_id"]             # Room code
                room_payload = row["room_data"]   # The room's data dictionary
                admin_summary_data.append({
                    "Room Access Code": r_id, 
                    "Creation Date": room_payload.get("created_at", "Legacy"),
                    "Total Dashboard Openings": room_payload.get("total_visits", 1), 
                    "Registered Players": len(room_payload.get("players", [])), # Count players
                    "Active Brackets": len(room_payload.get("matches", []))     # Count active matches
                })
    except Exception as e:
        st.error(f"Admin Data Retrieval Failure: {e}")
        
    # Show a big number of total active rooms
    st.metric(label="Total Created Activity Rooms", value=len(admin_summary_data))
        
    # Turn the collected data into a clean pandas table and display it
    if admin_summary_data:                                  
        df_admin = pd.DataFrame(admin_summary_data)         
        st.dataframe(df_admin, use_container_width=True)    
    else:
        st.info("System storage arrays are completely blank right now.") 
    
    st.stop() # Stop here. Admins don't need to see the badminton tabs.

# ==============================================================================
# 🗂️ SECTION 4: MAIN DASHBOARD LAYOUT & CORE BRACKET CALCULATIONS
# ==============================================================================

# Splitting the top of the screen into two columns for Title and Logout button
col1, col2 = st.columns([4, 1])                             
with col1:
    st.title(f"🏸 Match & Tournament Hub")
    st.caption(f"Active Live Cloud Room: **{room_code}**")      
with col2:
    # Logout logic: Deletes all temporary memory and clears the URL tracking
    if st.button("Change Room / Exit", use_container_width=True): 
        del st.session_state.room_id                        
        if "room_data" in st.session_state: del st.session_state.room_data                  
        if "room" in st.query_params: del st.query_params["room"]
        if "tab" in st.query_params: del st.query_params["tab"] 
        st.rerun()

st.markdown("---")

def generate_and_lock_teams(match_format, active_players):
    # PURPOSE: Shuffles the players who are present today and locks them into teams
    
    # Create a copy of the active players and randomize the order
    shuffled_pool = list(active_players)                               
    random.shuffle(shuffled_pool)                               
    
    # Clear out any old teams
    st.session_state.room_data["teams"] = []                    
    
    if match_format == "Singles":                               
        # For singles, every player is their own team
        for p in shuffled_pool:                                 
            st.session_state.room_data["teams"].append([p])     
    else:                                                       
        # For doubles, pop two players out of the shuffled list and group them
        while len(shuffled_pool) >= 2:                          
            st.session_state.room_data["teams"].append([shuffled_pool.pop(), shuffled_pool.pop()]) 
            
        # If there is 1 person left over (an odd number of players)
        if len(shuffled_pool) == 1:
            odd_player = shuffled_pool.pop()
            # Pair them with someone else who is already playing so they don't sit out
            for other_player in active_players:
                if other_player != odd_player:
                    st.session_state.room_data["teams"].append([odd_player, other_player])
            
    # Save the new locked teams to the cloud
    save_local_data(room_code, st.session_state.room_data)      

def log_match_to_history(match):
    # PURPOSE: Takes a completed match and permanently adds its stats to the leaderboards
    
    # Shortcuts to the leaderboard data
    ind_lb = st.session_state.room_data["ind_leaderboard"]      
    team_lb = st.session_state.room_data["team_leaderboard"]    
    
    # Create string names for the teams (e.g., "Alice & Bob") sorted alphabetically
    t_a_name = " & ".join(sorted(match["team_a"]))               
    t_b_name = " & ".join(sorted(match["team_b"]))               
    
    # If these teams have never played together before, create a blank profile for them
    if t_a_name not in team_lb: team_lb[t_a_name] = {"Wins": 0, "Points": 0}
    if t_b_name not in team_lb: team_lb[t_b_name] = {"Wins": 0, "Points": 0}
        
    # If the individual players have never played before, create blank profiles for them
    for p in match["team_a"] + match["team_b"]:
        if p not in ind_lb:
            ind_lb[p] = {"Wins": 0, "Points": 0, "Singles Played": 0, "Doubles Played": 0, "Grand Finals Won": 0}
        
    # Add the points scored in this match to the team totals
    team_lb[t_a_name]["Points"] += match["score_a"]             
    team_lb[t_b_name]["Points"] += match["score_b"]             
    
    # Add the points scored to each individual player's total
    for p in match["team_a"]: ind_lb[p]["Points"] += match["score_a"] 
    for p in match["team_b"]: ind_lb[p]["Points"] += match["score_b"] 
    
    # Determine what kind of match this was for specific stat tracking
    is_singles = len(match["team_a"]) == 1
    is_doubles = len(match["team_a"]) == 2
    is_gf = match.get("is_final", False) or "GRAND FINAL" in str(match.get("type", "")).upper()
    
    # Add to the "games played" counters for individuals
    for p in match["team_a"] + match["team_b"]:
        if is_singles: ind_lb[p]["Singles Played"] += 1
        elif is_doubles: ind_lb[p]["Doubles Played"] += 1

    # Figure out who won, and add 1 to their win counts
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
        
    # Save the updated leaderboards to the cloud
    save_local_data(room_code, st.session_state.room_data)      

# ==============================================================================
# 🏆 SECTION 5: NAVIGATION WORKSPACE TABS
# ==============================================================================

# Define the names of our three main tabs
tabs = ["👥 Roster & Expenses", "🎮 Matches & Play", "🏆 Leaderboards"] 

# 1. Determine which tab should be active based on the URL tracking
current_url_tab = st.query_params.get("tab", tabs[0])
# Fallback in case a user types a fake tab name in the URL
if current_url_tab not in tabs:
    current_url_tab = tabs[0]
# Find the numerical index (0, 1, or 2) of the requested tab
default_tab_idx = tabs.index(current_url_tab)

# 2. Render the navigation bar. It defaults to whatever tab was saved in the URL.
selected_tab = st.radio("Navigation Workspace:", tabs, index=default_tab_idx, horizontal=True, key="tab_navigation") 

# 3. Immediately update the URL if the user clicks a new tab. 
# THIS IS WHAT PREVENTS THE TAB FROM RESETTING ON REFRESH!
st.query_params["tab"] = selected_tab

# --- RENDER TAB CONTENT ---

if selected_tab == "👥 Roster & Expenses":
    col_p, col_e = st.columns(2)                                
    
    with col_p:
        st.subheader("Player Management")
        
        # Text box for adding a new player
        new_player = st.text_input("Add Player Name:")          
        if st.button("Add Player", type="primary"):
            # Ensure the box isn't empty, and the player doesn't already exist
            if new_player.strip() and new_player.strip() not in st.session_state.room_data["players"]:
                st.session_state.room_data["players"].append(new_player.strip()) 
                # Give them a starting expense balance of $0
                st.session_state.room_data["expenses"][new_player.strip()] = 0.0 
                save_local_data(room_code, st.session_state.room_data) 
                st.rerun()                                      
                
        st.markdown("#### Current Roster")
        # Loop through all players and display their name with a delete button
        for idx, player in enumerate(st.session_state.room_data["players"]):
            col_name, col_del = st.columns([5, 1])               
            col_name.write(f"• {player}")                        
            
            # If delete button is pressed:
            if col_del.button("🗑️", key=f"del_{player}_{idx}"):  
                st.session_state.room_data["players"].remove(player) 
                # Remove them from the expense ledger, but keep their stats in the leaderboard dict
                if player in st.session_state.room_data["expenses"]: del st.session_state.room_data["expenses"][player] 
                save_local_data(room_code, st.session_state.room_data) 
                st.rerun()

    with col_e:
        st.subheader("💰 Expense Ledger")
        # Loop through players and show a number input for how much they've paid
        for player in st.session_state.room_data["players"]:
            current_expense = st.session_state.room_data["expenses"].get(player, 0.0) 
            
            # The number input box for money
            updated = st.number_input(f"{player} Paid ($):", min_value=0.0, value=float(current_expense), step=1.0, key=f"exp_{player}")
            
            # If the user changed the money amount, save it to the cloud
            if updated != current_expense:                      
                st.session_state.room_data["expenses"][player] = updated 
                save_local_data(room_code, st.session_state.room_data) 
        
        st.markdown("---")
        # Button to wipe all expense data back to $0
        if st.session_state.room_data["expenses"] and st.button("🗑️ Reset Expense Ledger", type="secondary", use_container_width=True):
            for player in st.session_state.room_data["expenses"]: st.session_state.room_data["expenses"][player] = 0.0 
            save_local_data(room_code, st.session_state.room_data) 
            st.toast("💰 Expense records cleared back to $0.0!") 
            st.rerun()

elif selected_tab == "🎮 Matches & Play":
    col_cfg, col_play = st.columns([1, 2])                      
    
    with col_cfg:
        st.subheader("⚙️ Team Generation & Fixtures")
        
        st.markdown("#### 🎯 Today's Lineup")
        
        # A dropdown where the user selects who is actually in the session today.
        # Defaults to selecting everyone on the roster.
        active_players = st.multiselect(
            "Select players playing this session:",
            options=st.session_state.room_data["players"],
            default=st.session_state.room_data["players"],
            help="Remove anyone who is absent so they aren't placed on a team."
        )

        # Settings for the matches
        match_type = st.radio("Format:", ["Singles", "Doubles"], index=1) 
        max_pts = st.number_input("Target Points (Qualifiers):", value=15, min_value=1) 
        final_pts = st.number_input("Target Points (Grand Final):", value=21, min_value=1) 
        
        col_btn1, col_btn2 = st.columns(2)                       
        with col_btn1:
            # Button to trigger the lock teams function
            if st.button("👥 Lock Teams", use_container_width=True, type="secondary"):
                req = 2 if match_type == "Singles" else 4         
                if len(active_players) < req: 
                    st.error(f"Need at least {req} active players for this format!")    
                else:
                    generate_and_lock_teams(match_type, active_players)          
                    st.rerun()
                    
        with col_btn2:
            # Button to re-roll teams (does the exact same thing as Lock Teams, but visually framed as re-rolling)
            if st.button("🔓 Unlock & Re-roll", use_container_width=True): 
                req = 2 if match_type == "Singles" else 4
                if len(active_players) < req:
                    st.error(f"Need at least {req} active players for this format!")
                else:
                    generate_and_lock_teams(match_type, active_players)
                    st.rerun()

        # Display the locked teams to the user
        if st.session_state.room_data["teams"]:
            st.info("🔒 Teams: " + " | ".join([" & ".join(t) for t in st.session_state.room_data["teams"]]))
        else:
            st.warning("⚠️ No fixed teams locked yet.")

        st.divider()

        # Calculate how many teams we have, to suggest how many matches to generate
        num_teams = len(st.session_state.room_data["teams"])    
        m_count = st.number_input("Number of Matches to Draw:", min_value=1, value=max(1, num_teams)) 

        # Generate standard random matches
        if st.button("🎲 Draw Random Matches", use_container_width=True):
            if len(st.session_state.room_data["teams"]) < 2:
                st.error("Need at least 2 locked teams!")
            else:
                # Find all possible match-ups where players don't play against themselves
                valid_draw_pairs = []
                for team_a, team_b in itertools.combinations(st.session_state.room_data["teams"], 2):
                    if set(team_a).isdisjoint(set(team_b)):
                        valid_draw_pairs.append((team_a, team_b))
                
                if not valid_draw_pairs:
                    st.error("❌ Not enough non-overlapping team setups to generate a match.")
                else:
                    random.shuffle(valid_draw_pairs)                        
                    
                    # Create the temporary fixtures list
                    fixtures = []                                    
                    for i in range(int(m_count)):
                        pair = valid_draw_pairs[i % len(valid_draw_pairs)] # cycle through valid pairs       
                        fixtures.append({
                            "id": str(uuid.uuid4()), "type": "Round Match", "is_final": False, "logged": False,                         
                            "team_a": pair[0], "team_b": pair[1], "score_a": 0, "score_b": 0, "max_points": int(max_pts)               
                        })
                    st.session_state.room_data["matches"] = fixtures 
                    save_local_data(room_code, st.session_state.room_data) 
                    st.rerun()

        # Generate a Tournament Pack (Qualifiers + Grand Final)
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
                    # Add normal qualifiers
                    for i in range(int(m_count)):
                        pair = valid_draw_pairs[i % len(valid_draw_pairs)]
                        fixtures.append({
                            "id": str(uuid.uuid4()), "type": f"Qualifier #{i+1}", "is_final": False, "logged": False,
                            "team_a": pair[0], "team_b": pair[1], "score_a": 0, "score_b": 0, "max_points": int(max_pts)
                        })
                    # Add the TBD Grand final at the end
                    fixtures.append({
                        "id": str(uuid.uuid4()), "type": "GRAND FINAL", "is_final": True, "logged": False,
                        "team_a": ["TBD"], "team_b": ["TBD"], "score_a": 0, "score_b": 0, "max_points": int(final_pts) 
                    })
                    st.session_state.room_data["matches"] = fixtures
                    save_local_data(room_code, st.session_state.room_data)
                    st.rerun()

    with col_play:
        st.subheader("Live Scoreboard")
        # Clear matches button
        if st.session_state.room_data["matches"] and st.button("🗑️ Clear Current Fixtures"):
            st.session_state.room_data["matches"] = []          
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()
            
        # LIVE STANDINGS CALCULATION (for deciding who goes to the Grand Final)
        current_pack_stats = {}
        # First, ensure all teams start with 0 points/wins for this specific tournament
        for t in st.session_state.room_data["teams"]:
            t_key = " & ".join(t)
            current_pack_stats[t_key] = {"Wins": 0, "Points": 0, "TeamRaw": t} 

        # Calculate wins and points based ONLY on completed non-final matches in the current view
        for match in st.session_state.room_data["matches"]:
            if not match.get("is_final", False) and (match["score_a"] >= match["max_points"] or match["score_b"] >= match["max_points"]):
                t_a_str = " & ".join(match["team_a"])
                t_b_str = " & ".join(match["team_b"])
                
                # Make sure teams exist in dict
                if t_a_str not in current_pack_stats: current_pack_stats[t_a_str] = {"Wins": 0, "Points": 0, "TeamRaw": match["team_a"]}
                if t_b_str not in current_pack_stats: current_pack_stats[t_b_str] = {"Wins": 0, "Points": 0, "TeamRaw": match["team_b"]}
                
                # Add points to the live standings
                current_pack_stats[t_a_str]["Points"] += match["score_a"] 
                current_pack_stats[t_b_str]["Points"] += match["score_b"] 
                
                # Add wins to the live standings
                if match["score_a"] > match["score_b"]: current_pack_stats[t_a_str]["Wins"] += 1     
                else: current_pack_stats[t_b_str]["Wins"] += 1     

        # Sort the live standings by highest wins, then highest points
        sorted_pack_teams = sorted(current_pack_stats.values(), key=lambda x: (x["Wins"], x["Points"]), reverse=True)

        # RENDER THE SCOREBOARDS
        for idx, match in enumerate(st.session_state.room_data["matches"]):
            # If it's the Grand Final, inject the top 2 teams from sorted_pack_teams
            if match.get("is_final", False):                     
                st.markdown(f"### 🏆 GRAND FINAL — Race to {match['max_points']}")
                if len(sorted_pack_teams) >= 2:                  
                    match["team_a"] = sorted_pack_teams[0]["TeamRaw"] 
                    match["team_b"] = sorted_pack_teams[1]["TeamRaw"] 
            else:
                st.markdown(f"**Match #{idx + 1} ({match['type']})**") 
                
            col_t1, col_s1, col_vs, col_s2, col_t2 = st.columns([3, 1, 1, 1, 3]) 
            
            with col_t1: st.write(f"**{' & '.join(match['team_a'])}**") 
            
            # Score input for Team A
            with col_s1: 
                score_a = st.number_input("Team A", min_value=0, value=match["score_a"], key=f"a_{match['id']}", label_visibility="collapsed")
                if score_a != match["score_a"]:                  
                    match["score_a"] = score_a                   
                    save_local_data(room_code, st.session_state.room_data) 
            
            with col_vs: st.write("VS")
            
            # Score input for Team B
            with col_s2: 
                score_b = st.number_input("Team B", min_value=0, value=match["score_b"], key=f"b_{match['id']}", label_visibility="collapsed")
                if score_b != match["score_b"]:
                    match["score_b"] = score_b
                    save_local_data(room_code, st.session_state.room_data)
            
            with col_t2: st.write(f"**{' & '.join(match['team_b'])}**")
            
            # If the match has reached the max score (game over)
            if match["score_a"] >= match["max_points"] or match["score_b"] >= match["max_points"]:
                # If this match hasn't been logged to the all-time leaderboard yet, do it now
                if not match.get("logged", False):               
                    match["logged"] = True                       
                    log_match_to_history(match)                  
                    st.rerun()                                   
                
                # Success messages
                if match.get("is_final", False):                 
                    champ = ' & '.join(match['team_a']) if match['score_a'] > match['score_b'] else ' & '.join(match['team_b'])
                    st.balloons()                                
                    st.success(f"👑 {champ} WINS THE TOURNAMENT CHAMPIONSHIP! 👑") 
                else:
                    st.success("✅ Saved to Leaderboard!")
            st.divider()                                         

elif selected_tab == "🏆 Leaderboards":
    st.subheader("📈 All-Time Standings")
    
    # Shortcuts to the all-time stats dictionaries
    ind_stats = st.session_state.room_data["ind_leaderboard"]    
    team_stats = st.session_state.room_data["team_leaderboard"]   
    
    col_l1, col_l2 = st.columns(2)                                
    with col_l1:
        st.markdown("### 🥇 Individual Leaderboard")
        
        # Combine current roster and historically tracked players.
        # This prevents players from vanishing from the leaderboard if they get deleted from the Roster page.
        all_tracked_players = set(st.session_state.room_data.get("players", [])) | set(ind_stats.keys())
        
        # Format the dictionary so Pandas can turn it into a clean table
        display_profiles = {}
        for player in all_tracked_players:
            saved_profile = ind_stats.get(player, {})
            # Only display players who have actually logged a match or are in the current roster
            display_profiles[player] = {
                "Wins": saved_profile.get("Wins", 0), 
                "Singles Played": saved_profile.get("Singles Played", 0),
                "Doubles Played": saved_profile.get("Doubles Played", 0), 
                "Grand Finals Won": saved_profile.get("Grand Finals Won", 0),
                "Total points scored": saved_profile.get("Points", 0)
            }
            
        if display_profiles:     
            # Create a Pandas DataFrame (table) and sort it by GF Wins, then regular Wins, then Points.                                       
            df_ind = pd.DataFrame.from_dict(display_profiles, orient='index').sort_values(by=["Grand Finals Won", "Wins", "Total points scored"], ascending=[False, False, False])
            st.dataframe(df_ind, use_container_width=True)       
        else: st.info("No stats available.")
            
    with col_l2:
        st.markdown("### 🏅 Team Leaderboard")
        if team_stats:
            # Create a Pandas table for teams, sorting by Wins, then Points
            df_team = pd.DataFrame.from_dict(team_stats, orient='index').sort_values(by=["Wins", "Points"], ascending=[False, False])
            st.dataframe(df_team, use_container_width=True)
        else: st.info("No stats available.")

    st.markdown("---")
    
    # Danger zone buttons
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        if st.button("⚠️ Hard Reset Leaderboards", use_container_width=True, type="secondary"):
            # Wipes all historical stats clean
            st.session_state.room_data["ind_leaderboard"] = {}   
            st.session_state.room_data["team_leaderboard"] = {}  
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()
    with col_r2:
        if st.button("🔄 Dissolve Fixed Teams List", use_container_width=True):
            # Wipes the current locked teams so you can re-roll with new players
            st.session_state.room_data["teams"] = []             
            save_local_data(room_code, st.session_state.room_data) 
            st.rerun()