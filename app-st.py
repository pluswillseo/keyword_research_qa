import csv
from collections import defaultdict
from fuzzywuzzy import fuzz
import streamlit as st
import pandas as pd
from spellchecker import SpellChecker
import re
import time
import io

st.set_page_config(page_title="Keyword QA Tool | Fix Near Duplicates & Misspellings", layout = "wide", initial_sidebar_state="auto")

st.title("Keyword Research Quality Assurance Review")

st.markdown("""
<style>
.big-font {
    font-size:20px !important;
}
.medium-font {
    font-size:10px !important;
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="big-font">Utilise this application to help you review or conduct a keyword research and help you complete the following:<p>', unsafe_allow_html=True)
st.write("👉 **Find near duplicate keywords that have the same search volume** (e.g. 'shoes' and 'shoe') - if they have the same search volume they're likely grouped and therefore keeping both will be inflating your data")
st.write("👉 Misspellings - sometimes the smallest errors are the hardest - working out somehting is spelled wrong (see what I did there?) - **this app will highlight potential misspellings**")
st.write("👉 **Special characters - this will highlight as a 'misspelling' if it sees a special character used**")
st.write("👉 **Find duplicates with/without 's' - Column 'duplicate with 's'' is a true/false column highlighting where a keyword has a 's' duplicate with the same search volume. That means you can filter out instances of 'true' and you immediately remove these grouped keywords without requiring review**")

st.write("How to use: ")
st.write("1. Input a CSV with your Keyword and Search Volume columns. This should then populate into a table below.")
st.write("2. You can then use the similarity threshold to determine how similar you want the keywords to be that are listed.")
st.write("3. Ensure that any branded or product names (or anything you want to be excluded from spellcheck) are listed in the ignore list, using commas between each.")
st.write("4. Select the desired delimiter - this is set to default ","")
st.write("5. Once your happy and the table has populated below, export the table below!")

st.write("**Important notes:**")
st.write("**- Please save csv as CSV UTF-8 (delimited) with column headers (Keywords and Search Volume) as the first row is ignored**")
st.write("**- If you have a list of keywords in another language other than english, the misspellings column will not be accurate, but you can still use the similarity column**")

st.text("")
st.text("")

ignore_words = st.text_input("Add all words you want to ignore as part of the spell check, such as branded terms, product lines, etc.")

st.text("")
st.text("")

sim_score = st.slider("What similarity score do you want to use for your dataset? The default is 96, however you can adapt as you see necessary between 90 and 100", min_value=90, max_value=100, value=96)

st.text("")
st.text("")

dl = st.radio(
        "What delimiter are you using?",
        (",", ";", "\t", "|"),
        index=0,
        horizontal=True
    )

st.write('The current selected delimiter is "', dl, '"')

st.text("")

# Add a sidebar to the app
#st.sidebar.title("Filter misspellings (not currently working)")

# Add a filter to the sidebar that allows users to select multiple categories
#selected_categories = st.sidebar.multiselect("Select categories to filter by:", ["", "Potential misspelling or error"])

# Read the input csv file
uploaded_file = st.file_uploader("Choose a CSV file with keywords and SV to process - this should have keywords in first column, and search volume in the second", type='csv')

if uploaded_file is not None:
    
    import io
        
    csv_reader = csv.reader(io.TextIOWrapper(uploaded_file, encoding="utf-8"), delimiter=dl)
    
    placeholder = st.empty()
    placeholder.progress(10)

    #skip first row
    next(csv_reader)
    placeholder.progress(20)
    
    #create a list to store the rows
    rows = []

    for row in csv_reader:
        rows.append(row)

    # Create a dictionary to store the groupings
    groups = defaultdict(list)
    placeholder.progress(30)

    # Iterate over the rows in the csv file
    for row in rows:
        # Get the keyword and search volume from the row
        keyword = row[0]
        search_volume = row[1]

        # Add the keyword to the appropriate group based on its search volume
        groups[search_volume].append(keyword)

    # Create a dictionary to store the results
    results = {}
    placeholder.progress(40)
    st.success("Completed loading and grouping keywords by search volume. Now looking for similar keywords in each grouping...this can take a while...")    
    # Iterate over the groups
    for search_volume, keywords in groups.items():
        # Iterate over the keywords in each group
        for keyword in keywords:
            # Iterate over the other keywords in the group
            for other_keyword in keywords:
                # Skip the keyword if it's the same as the other keyword
                if keyword == other_keyword:
                    continue

                # Calculate the fuzzy similarity score between the keyword and the other keyword
                score = fuzz.token_sort_ratio(keyword, other_keyword)

                # Only store the results if the similarity score is 80 or higher
                if score >= sim_score:
                    # If the keyword is not already in the results dictionary, add it
                    if keyword not in results:
                        results[keyword] = []

                    # Add the other keyword to the list of similar keywords for the keyword
                    results[keyword].append(other_keyword)
    
    placeholder.progress(50)

    # Create a list of rows for the data frame
    data = []
    
    placeholder.progress(60)
    
    # Iterate over the rows in the input csv file
    for row in rows:
        # Get the keyword and search volume from the row
        keyword = row[0]
        search_volume = row[1]

        # Get the list of similar keywords for the keyword
        similar_keywords = results.get(keyword, [])

        # Join the list of similar keywords with a ", "
        similar_keywords_str = ", ".join(similar_keywords)

        # Add the results for the current row to the list of rows
        data.append([keyword, search_volume, similar_keywords_str])

    # Create a pandas DataFrame to store the results
    df = pd.DataFrame(data, columns=["Keyword", "Search Volume", "Similar Keywords"])
    
    # Create a new column with modified versions of the Keyword column
    df["Keyword_modified"] = df["Keyword"].apply(lambda x: x + "s")
    
    #create new column
    df["Duplicate with 's'"] = False
    
    keywords = df["Keyword"].tolist()
    
    #iterate through each keyword
    for keyword in keywords:
        mask = df["Keyword_modified"].isin([keyword])
        df.loc[mask, "Duplicate with 's'"] = True
        
    # drop the column you no longer need
    df = df.drop("Keyword_modified", axis = 1)
    
    keywords = df['Keyword']
    placeholder.progress(70)

    df['Misspelling or special character'] = ""

    # initialize the spell checker
    spell_checker = SpellChecker()
    
    def check_misspellings(df, ignore_list):

        # define a regular expression to match any special characters
        regex = r'[^A-Za-z0-9 ]'

        # iterate over the keywords and check for any misspellings or special characters
        for keyword in keywords:

        # split the keyword into individual words
            words = keyword.split()

        # iterate over the words and check for any misspellings or special characters
            for word in words:
                # skip any words that are in the ignore list
                if word in ignore_list:
                    continue

                if len(spell_checker.unknown([word])) > 0 or re.search(regex, word):
                    df.loc[df['Keyword'] == keyword, 'Misspelling or special character'] = "Potential misspelling or error"
                    break
        return df
    
    # define a list of words to ignore (e.g. brand names, product names, etc.)
    ignore_list = [k.strip() for k in ignore_words.split(",")]
    df = check_misspellings(df, ignore_list)
    placeholder.progress(90)
                
    placeholder.progress(100)
    st.empty().success('Completed the table!')

#all new below
    # Create a filtered dataframe using the selected filters
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("Filter misspellings")
        st.write("Once you've reviewed the output and you're happy that you no longer need any of the keywords marked misspelled, then use this filter to remove them")
        selected_categories = st.multiselect('Filter out misspellings/special characters', df['Misspelling or special character'].unique())
    with col2:
        st.header("Filter out keyword that only differ by 's'")
        st.write("This table marks the non 's' version if there are 2 duplicate keywords with the same search volume, but one including 's', this document will mark one of the 2 as True, meaning you can easily filter it out.")
        duplicate_s = st.multiselect('Filter out non s duplicates with same search volume', df["Duplicate with 's'"].unique())
    
    if selected_categories and duplicate_s:
        filtered_df = df[(df['Misspelling or special character'].isin(selected_categories)) & (df["Duplicate with 's'"].isin(duplicate_s))]
    elif selected_categories:
        filtered_df = df[df['Misspelling or special character'].isin(selected_categories)]
    elif duplicate_s:
        filtered_df = df[df["Duplicate with 's'"].isin(duplicate_s)]             
    else:
        filtered_df = df

    csv = filtered_df.to_csv(index=False)
    st.download_button('Download Table as CSV', csv, file_name = 'output.csv', mime='text/csv')
    st.table(filtered_df) 
