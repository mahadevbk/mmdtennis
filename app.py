import streamlit as st
import pandas as pd
from datetime import datetime
import os
import traceback

# Load or initialize data
def load_data():
    try:
        if os.path.exists('players.csv'):
            players = pd.read_csv('players.csv')
            if 'name' not in players.columns:
                players = pd.DataFrame(columns=['name'])
        else:
            players = pd.DataFrame(columns=['name'])
        
        if os.path.exists('matches.csv'):
            matches = pd.read_csv('matches.csv')
        else:
            matches = pd.DataFrame(columns=['Date', 'Type', 'Player1', 'Player2', 'Player3', 'Player4', 
                                          'Set1', 'Set2', 'Set3', 'Winners'])
        return players, matches
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return pd.DataFrame(columns=['name']), pd.DataFrame(columns=['Date', 'Type', 'Player1', 'Player2', 'Player3', 'Player4', 
                                                                   'Set1', 'Set2', 'Set3', 'Winners'])

def save_data(players, matches):
    try:
        players.to_csv('players.csv', index=False)
        matches.to_csv('matches.csv', index=False)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

def calculate_points_wins_games(matches):
    points = {}
    match_wins = {}
    games_won = {}
    try:
        for _, match in matches.iterrows():
            winners = [w for w in match['Winners'].split(',') if w and w != 'None' and pd.notna(w)]
            all_players = [p for p in [match['Player1'], match['Player2'], match['Player3'], match['Player4']] 
                          if p and p != 'None' and pd.notna(p)]
            losers = [p for p in all_players if p not in winners]
            
            # Calculate points
            for winner in winners:
                points[winner] = points.get(winner, 0) + 3
                match_wins[winner] = match_wins.get(winner, 0) + 1
            for loser in losers:
                points[loser] = points.get(loser, 0) + 1
            
            # Calculate games won from sets
            team1 = [match['Player1'], match['Player2']] if match['Type'] == 'Doubles' else [match['Player1']]
            team2 = [match['Player3'], match['Player4']] if match['Type'] == 'Doubles' else [match['Player2']]
            
            for set_col in ['Set1', 'Set2', 'Set3']:
                if pd.notna(match[set_col]) and match[set_col]:
                    score = match[set_col].split('-')
                    if len(score) == 2:
                        try:
                            games_team1, games_team2 = int(score[0]), int(score[1])
                            for player in team1:
                                games_won[player] = games_won.get(player, 0) + games_team1
                            for player in team2:
                                games_won[player] = games_won.get(player, 0) + games_team2
                        except ValueError:
                            continue  # Skip if score format is invalid
    except Exception as e:
        st.error(f"Error calculating points, wins, and games: {str(e)}")
    return points, match_wins, games_won

def get_player_stats(player, matches):
    try:
        player_matches = matches[(matches['Player1'] == player) | 
                               (matches['Player2'] == player) | 
                               (matches['Player3'] == player) | 
                               (matches['Player4'] == player)]
        
        dates = pd.to_datetime(player_matches['Date']).dt.date.unique()
        frequency = len(dates)
        
        partners = {}
        for _, match in player_matches.iterrows():
            if match['Type'] == 'Doubles':
                players = [p for p in [match['Player1'], match['Player2'], match['Player3'], match['Player4']] 
                          if p and p != 'None' and pd.notna(p)]
                team = [match['Player1'], match['Player2']] if player in [match['Player1'], match['Player2']] else [match['Player3'], match['Player4']]
                valid_partners = [p for p in team if p != player and p != 'None' and pd.notna(p)]
                if valid_partners:
                    partner = valid_partners[0]
                    if partner not in partners:
                        partners[partner] = {'wins': 0, 'total': 0}
                    partners[partner]['total'] += 1
                    if player in match['Winners'].split(','):
                        partners[partner]['wins'] += 1
        
        best_partner = max(partners.items(), key=lambda x: x[1]['wins']/x[1]['total'] if x[1]['total'] > 0 else 0)[0] if partners else None
        
        return frequency, list(partners.keys()), best_partner
    except Exception as e:
        st.error(f"Error in get_player_stats: {str(e)}")
        return 0, [], None

def main():
    try:
        st.title("MMD Tennis Community")
        
        # Load data
        players_df, matches_df = load_data()
        
        # Sidebar
        st.sidebar.header("Manage Players")
        new_player = st.sidebar.text_input("Add New Player")
        if st.sidebar.button("Add Player") and new_player:
            if 'name' in players_df.columns and not players_df.empty:
                if new_player not in players_df['name'].tolist():
                    players_df = pd.concat([players_df, pd.DataFrame({'name': [new_player]})], ignore_index=True)
                    save_data(players_df, matches_df)
                    st.sidebar.success(f"Added {new_player}")
            else:
                players_df = pd.DataFrame({'name': [new_player]})
                save_data(players_df, matches_df)
                st.sidebar.success(f"Added {new_player}")

        # Delete player
        player_to_delete = st.sidebar.selectbox("Delete Player", [''] + players_df['name'].tolist() if 'name' in players_df.columns and not players_df.empty else [''])
        if st.sidebar.button("Delete Player") and player_to_delete:
            if st.sidebar.checkbox(f"Confirm deletion of {player_to_delete}"):
                players_df = players_df[players_df['name'] != player_to_delete]
                matches_df = matches_df[~matches_df[['Player1', 'Player2', 'Player3', 'Player4']].eq(player_to_delete).any(axis=1)]
                save_data(players_df, matches_df)
                st.sidebar.success(f"Deleted {player_to_delete}")

        # Get player list after potential updates
        player_list = players_df['name'].tolist() if 'name' in players_df.columns and not players_df.empty else []
        
        if not player_list:
            st.warning("No players found. Please add some players first using the sidebar.")
            return

        # Define possible tennis set scores
        set_scores = ['6-0', '6-1', '6-2', '6-3', '6-4', '7-5', '7-6', '0-6', '1-6', '2-6', '3-6', '4-6', '5-7', '6-7']

        # Match entry
        st.sidebar.header("Enter Match")
        match_date = st.sidebar.date_input("Match Date", value=datetime.now())
        match_type = st.sidebar.selectbox("Match Type", ["Singles", "Doubles"])
        
        if match_type == "Singles":
            player1 = st.sidebar.selectbox("Player 1", player_list)
            player2 = st.sidebar.selectbox("Player 2", player_list, index=1 if len(player_list) > 1 else 0)
            player3 = player4 = None
        else:
            st.sidebar.write("Team 1")
            player1 = st.sidebar.selectbox("Team 1 - Player 1", player_list)
            player2 = st.sidebar.selectbox("Team 1 - Player 2", player_list, index=1 if len(player_list) > 1 else 0)
            st.sidebar.write("Team 2")
            player3 = st.sidebar.selectbox("Team 2 - Player 1", player_list, index=2 if len(player_list) > 2 else 0)
            player4 = st.sidebar.selectbox("Team 2 - Player 2", player_list, index=3 if len(player_list) > 3 else 0)
        
        set1 = st.sidebar.selectbox("Set 1", [''] + set_scores)
        set2 = st.sidebar.selectbox("Set 2", [''] + set_scores)
        set3 = st.sidebar.selectbox("Set 3 (optional)", [''] + set_scores)
        
        if match_type == "Singles":
            winner = st.sidebar.selectbox("Winner", [player1, player2])
            winners = winner
        else:
            winner_team = st.sidebar.radio("Winning Team", ["Team 1", "Team 2"])
            winners = f"{player1},{player2}" if winner_team == "Team 1" else f"{player3},{player4}"
        
        if st.sidebar.button("Submit Match"):
            new_match = pd.DataFrame({
                'Date': [match_date.strftime('%Y-%m-%d')],
                'Type': [match_type],
                'Player1': [player1],
                'Player2': [player2],
                'Player3': [player3],
                'Player4': [player4],
                'Set1': [set1],
                'Set2': [set2],
                'Set3': [set3],
                'Winners': [winners]
            })
            matches_df = pd.concat([matches_df, new_match], ignore_index=True)
            save_data(players_df, matches_df)
            st.sidebar.success("Match recorded!")

        # Edit/Delete matches
        st.sidebar.header("Manage Matches")
        if not matches_df.empty:
            match_options = [f"{row['Date']} - {row['Type']} - {row['Player1']} vs {row['Player2']}" if row['Type'] == 'Singles' 
                            else f"{row['Date']} - {row['Type']} - {row['Player1']}/{row['Player2']} vs {row['Player3']}/{row['Player4']}"
                            for _, row in matches_df.iterrows()]
            match_to_manage = st.sidebar.selectbox("Select Match to Manage", [''] + match_options)
            
            if match_to_manage:
                match_index = matches_df.index[matches_df.apply(lambda row: 
                    f"{row['Date']} - {row['Type']} - {row['Player1']} vs {row['Player2']}" if row['Type'] == 'Singles'
                    else f"{row['Date']} - {row['Type']} - {row['Player1']}/{row['Player2']} vs {row['Player3']}/{row['Player4']}",
                    axis=1) == match_to_manage][0]
                
                # Edit match
                if st.sidebar.button("Edit Match"):
                    st.session_state['edit_match'] = match_index
                
                # Delete match with confirmation
                delete_key = f"delete_match_{match_index}"
                if st.sidebar.button("Delete Match", key=f"delete_button_{match_index}"):
                    st.session_state[delete_key] = True
                
                if delete_key in st.session_state and st.session_state[delete_key]:
                    if st.sidebar.checkbox(f"Confirm deletion of match {match_to_manage}"):
                        matches_df = matches_df.drop(match_index)
                        save_data(players_df, matches_df)
                        st.sidebar.success("Match deleted!")
                        del st.session_state[delete_key]
                        if 'edit_match' in st.session_state:
                            del st.session_state['edit_match']

                # Edit form
                if 'edit_match' in st.session_state and st.session_state['edit_match'] == match_index:
                    with st.sidebar:
                        st.write("Edit Match")
                        match = matches_df.loc[match_index]
                        edit_date = st.date_input("Match Date", value=pd.to_datetime(match['Date']).date())
                        edit_type = st.selectbox("Match Type", ["Singles", "Doubles"], index=0 if match['Type'] == "Singles" else 1)
                        
                        if edit_type == "Singles":
                            edit_p1 = st.selectbox("Player 1", player_list, index=player_list.index(match['Player1']))
                            edit_p2 = st.selectbox("Player 2", player_list, index=player_list.index(match['Player2']))
                            edit_p3 = edit_p4 = None
                        else:
                            edit_p1 = st.selectbox("Team 1 - Player 1", player_list, index=player_list.index(match['Player1']))
                            edit_p2 = st.selectbox("Team 1 - Player 2", player_list, index=player_list.index(match['Player2']))
                            edit_p3 = st.selectbox("Team 2 - Player 1", player_list, index=player_list.index(match['Player3']) if match['Player3'] else 0)
                            edit_p4 = st.selectbox("Team 2 - Player 2", player_list, index=player_list.index(match['Player4']) if match['Player4'] else 0)
                        
                        edit_set1 = st.selectbox("Set 1", [''] + set_scores, index=set_scores.index(match['Set1']) + 1 if match['Set1'] in set_scores else 0)
                        edit_set2 = st.selectbox("Set 2", [''] + set_scores, index=set_scores.index(match['Set2']) + 1 if match['Set2'] in set_scores else 0)
                        edit_set3 = st.selectbox("Set 3 (optional)", [''] + set_scores, index=set_scores.index(match['Set3']) + 1 if match['Set3'] in set_scores else 0)
                        
                        if edit_type == "Singles":
                            edit_winner = st.selectbox("Winner", [edit_p1, edit_p2], index=0 if match['Winners'] == match['Player1'] else 1)
                            edit_winners = edit_winner
                        else:
                            edit_winner_team = st.radio("Winning Team", ["Team 1", "Team 2"], index=0 if match['Winners'] == f"{match['Player1']},{match['Player2']}" else 1)
                            edit_winners = f"{edit_p1},{edit_p2}" if edit_winner_team == "Team 1" else f"{edit_p3},{edit_p4}"
                        
                        if st.button("Save Changes"):
                            matches_df.loc[match_index] = [edit_date.strftime('%Y-%m-%d'), edit_type, edit_p1, edit_p2, edit_p3, edit_p4,
                                                          edit_set1, edit_set2, edit_set3, edit_winners]
                            save_data(players_df, matches_df)
                            st.success("Match updated!")
                            del st.session_state['edit_match']

        # Main content
        tab1, tab2 = st.tabs(["Match History", "Player Stats"])
        
        with tab1:
            st.header("Match History")
            if not matches_df.empty:
                matches_display = matches_df.reset_index(drop=True)
                matches_display.index = matches_display.index + 1
                st.dataframe(matches_display)
            else:
                st.dataframe(matches_df)
        
        with tab2:
            st.header("Player Statistics")
            
            points, match_wins, games_won = calculate_points_wins_games(matches_df)
            # Create DataFrame with all metrics
            points_df = pd.DataFrame({
                'Player Name': list(points.keys()),
                'Points': list(points.values()),
                'Match Wins': [match_wins.get(player, 0) for player in points.keys()],
                'Games Won': [games_won.get(player, 0) for player in points.keys()]
            })
            # Sort by Points, Match Wins, Games Won (all descending)
            points_df = points_df.sort_values(by=['Points', 'Match Wins', 'Games Won'], ascending=[False, False, False])
            # Reset index and add Rank explicitly as a column
            points_df = points_df.reset_index(drop=True)
            points_df['Rank'] = points_df.index + 1
            # Select columns for display
            points_df_display = points_df[['Rank', 'Player Name', 'Points']]
            
            # Remove any rows where Player Name is 'None' or None
            points_df_display = points_df_display[points_df_display['Player Name'].notna() & (points_df_display['Player Name'] != 'None')]
            
            st.subheader("Points Leaderboard")
            st.dataframe(points_df_display, use_container_width=True, hide_index=True)
            
            # Debugging: Show full sorted DataFrame with all metrics
            st.subheader("Player : Full Sorted Stats")
            st.dataframe(points_df, use_container_width=True, hide_index=True)
            
            selected_player = st.selectbox("Select Player", player_list)
            if selected_player:
                frequency, partners, best_partner = get_player_stats(selected_player, matches_df)
                st.write(f"Points: {points.get(selected_player, 0)}")
                st.write(f"Match Wins: {match_wins.get(selected_player, 0)}")
                st.write(f"Games Won: {games_won.get(selected_player, 0)}")
                st.write(f"Match Frequency: {frequency} days")
                st.write(f"Partners: {', '.join(partners) if partners else 'None'}")
                st.write(f"Best Partner: {best_partner if best_partner else 'N/A'}")

    except Exception as e:
        st.error(f"Error in main application: {str(e)}\n\n{traceback.format_exc()}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Critical error launching app: {str(e)}\n{traceback.format_exc()}")
