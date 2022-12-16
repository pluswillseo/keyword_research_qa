import csv
from collections import defaultdict
from fuzzywuzzy import fuzz
import streamlit as st
import pandas as pd
from spellchecker import SpellChecker
import re
import time
import io

st.title("Keyword Research Fuzzy Lookup & Quality Assurance Review")

st.write("Utilise this document to complete the following:")
st.write("👉 Find near duplicate keywords that have the same search volume (e.g. 'shoes' and 'shoe') - if they have the same search volume they're likely grouped and therefore keeping both will be inflating your data")
st.write("👉 Misspellings - sometimes the smallest errors are the hardest - working out somehting is spelled wrong (see what I did there?)")
st.write("👉 Special characters - this will highlight as a 'misspelling' if it sees a special character used")

ignore_words = st.text_input("Add all words you want to ignore as part of the spell check, such as branded terms, product lines, etc.")
sim_score = st.slider("What similarity score do you want to use for your dataset? The default is 96, however you can adapt as you see necessary between 90 and 100", min_value=90, max_value=100, value=96)

# Read the input csv file
uploaded_file = st.file_uploader("Choose a CSV file with keywords and SV to process - this should have keywords in first column, and search volume in the second", type='csv')
if uploaded_file is not None:
    
    import io
    csv_reader = csv.reader(io.TextIOWrapper(uploaded_file, encoding="utf-8"), delimiter=",")
    
    #skip first row
    next(csv_reader)
    
    #create a list to store the rows
    rows = []

    for row in csv_reader:
        rows.append(row)

    # Create a dictionary to store the groupings
    groups = defaultdict(list)

    # Iterate over the rows in the csv file
    for row in rows:
        # Get the keyword and search volume from the row
        keyword = row[0]
        search_volume = row[1]

        # Add the keyword to the appropriate group based on its search volume
        groups[search_volume].append(keyword)

    # Create a dictionary to store the results
    results = {}

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

    # Create a list of rows for the data frame
    data = []


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
    
    keywords = df['Keyword']

    df['Misspelling'] = ""

    # initialize the spell checker
    spell_checker = SpellChecker()

    # define a regular expression to match any special characters
    regex = r'[^A-Za-z0-9 ]'

# define a list of words to ignore (e.g. brand names, product names, etc.)
    ignore_list = [k.strip() for k in ignore_words.split(",")]

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
                df.loc[df['Keyword'] == keyword, 'Misspelling'] = "Potential misspelling or error"
                break


# open the CSV file and write the updated keywords
#with open('output.csv', 'w', newline="") as csvfile:
#   writer = csv.writer(csvfile)
#   writer.writerows(keywords)

    # Display the DataFrame as a table
    st.dataframe(df)

    csv = df.to_csv(index=False)

    st.download_button('Download Table as CSV', csv, file_name = 'output.csv', mime='text/csv')
    
