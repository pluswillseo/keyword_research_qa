import csv
from collections import defaultdict
from fuzzywuzzy import fuzz
import streamlit as st
import pandas as pd
from spellchecker import SpellChecker
import re
import time
import io

st.set_page_config(page_title="Keyword QA Tool | Fix Near Duplicates & Misspellings", layout="wide", initial_sidebar_state="auto")

st.title("Keyword Research Quality Assurance Review")

st.markdown("""
<style>
.big-font { font-size:20px !important; }
.medium-font { font-size:10px !important; }
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
st.write("4. Select the desired delimiter - this is set to default ", "")
st.write("5. Once you're happy and the table has populated below, export the table below!")

st.write("**Important notes:**")
st.write("**- Please save csv as CSV UTF-8 (delimited) with column headers (Keywords and Search Volume) as the first row is ignored**")
st.write("**- If you have a list of keywords in another language other than english, the misspellings column will not be accurate, but you can still use the similarity column**")

st.text("")
st.text("")

# ✅ New options
group_keywords = st.checkbox("Group similar keywords (by Search Volume + fuzzy match)", value=True)
run_spellcheck = st.checkbox("Run spell check & special-character detection", value=True)

ignore_words = st.text_input("Add all words you want to ignore as part of the spell check, such as branded terms, product lines, etc.")
st.text("")
lang_select = st.text_input("Select language for misspelling review (e.g. en, es, fr, pt, de, it, ru, ar, eu, lv, nl)", value="en")
st.text("")
sim_score = st.slider("Similarity score (default 96). Adjust 90–100:", min_value=90, max_value=100, value=96)
st.text("")

dl = st.radio(
    "What delimiter are you using?",
    (",", ";", "\t", "|"),
    index=0,
    horizontal=True
)
st.write('The current selected delimiter is "', dl, '"')
st.text("")

uploaded_file = st.file_uploader(
    "Choose a CSV file with keywords and SV to process - this should have keywords in first column, and search volume in the second",
    type='csv'
)

if uploaded_file is not None:
    csv_reader = csv.reader(io.TextIOWrapper(uploaded_file, encoding="utf-8"), delimiter=dl)

    placeholder = st.empty()
    placeholder.progress(5)

    # Skip header row
    try:
        next(csv_reader)
    except StopIteration:
        st.error("File appears empty after header row.")
        st.stop()

    # Load all rows
    rows = [row for row in csv_reader if row]
    placeholder.progress(15)

    # Base data list
    data = []
    for row in rows:
        # Robustness: handle short rows
        kw = row[0] if len(row) > 0 else ""
        sv = row[1] if len(row) > 1 else ""
        data.append([kw, sv])

    df = pd.DataFrame(data, columns=["Keyword", "Search Volume"])
    placeholder.progress(25)

    # ===== GROUPING (optional) =====
    if group_keywords:
        st.info("Grouping similar keywords by search volume — this can take a while on large files.")
        groups = defaultdict(list)
        for kw, sv in zip(df["Keyword"], df["Search Volume"]):
            groups[sv].append(kw)
        placeholder.progress(35)

        results = {}
        processed_groups = 0
        total_groups = len(groups)

        for sv, keywords_in_group in groups.items():
            # Compare each keyword to others in the same SV group
            for keyword in keywords_in_group:
                for other_keyword in keywords_in_group:
                    if keyword == other_keyword:
                        continue
                    score = fuzz.token_sort_ratio(keyword, other_keyword)
                    if score >= sim_score:
                        results.setdefault(keyword, []).append(other_keyword)
            processed_groups += 1
            if processed_groups % 10 == 0:
                placeholder.progress(35 + int(30 * processed_groups / max(1, total_groups)))

        df["Similar Keywords"] = df["Keyword"].apply(lambda k: ", ".join(results.get(k, [])))
    else:
        df["Similar Keywords"] = ""  # Keep column for consistency
        placeholder.progress(50)

    # ===== DUPLICATE 's' COLUMN (always computed) =====
    df["Keyword_modified"] = df["Keyword"].apply(lambda x: f"{x}s")
    df["Duplicate with 's'"] = False
    keywords_list = df["Keyword"].tolist()
    mask = df["Keyword_modified"].isin(keywords_list)
    df.loc[mask, "Duplicate with 's'"] = True
    df.drop(columns=["Keyword_modified"], inplace=True)
    placeholder.progress(65)

    # ===== SPELLCHECK (optional) =====
    if run_spellcheck:
        df['Misspelling or special character'] = ""
        # Initialise spell checker with fallback
        try:
            spell_checker = SpellChecker(language=lang_select.strip().lower() or "en")
            # Access to force dictionary load early, catching unsupported languages
            _ = spell_checker.unknown(["test"])
        except Exception:
            st.warning(f"Language '{lang_select}' not supported by pyspellchecker. Falling back to English.")
            spell_checker = SpellChecker(language="en")

        ignore_list = [k.strip() for k in ignore_words.split(",") if k.strip()]
        ignore_set = set(w.lower() for w in ignore_list)

        # regex to flag any special characters (keep it as in your original)
        regex = re.compile(r"[^\w\s]", re.UNICODE)

        def check_row(keyword: str) -> str:
            bad_parts = []
            for word in keyword.split():
                lw = word.lower()
                if lw in ignore_set:
                    continue
                if regex.search(word) or len(spell_checker.unknown([lw])) > 0:
                    bad_parts.append(word)
            return ", ".join(bad_parts)

        # Vectorised-ish apply
        df['Misspelling or special character'] = df['Keyword'].apply(check_row)
    else:
        # Still include the column for downstream filters if you want; leave blank
        df['Misspelling or special character'] = ""
    placeholder.progress(85)

    # ===== FILTERS =====
    st.success("Completed processing. Use filters or download the table below.")

    col1, col2 = st.columns(2)

    if run_spellcheck:
        with col1:
            st.header("Filter misspellings")
            st.write("Remove rows based on detected misspellings/special characters.")
            misspell_options = [x for x in df['Misspelling or special character'].unique() if x]
            selected_categories = st.multiselect(
                'Filter out misspellings/special characters',
                misspell_options
            )
    else:
        selected_categories = []
        with col1:
            st.header("Filter misspellings")
            st.write("Spell check not run (checkbox above).")

    with col2:
        st.header("Filter out keywords that only differ by 's'")
        st.write("Marks the non-'s' version if there are duplicate keywords with the same search volume.")
        duplicate_s = st.multiselect(
            "Filter out non-'s' duplicates with same search volume",
            df["Duplicate with 's'"].unique()
        )

    # Build filtered view
    if selected_categories and duplicate_s:
        filtered_df = df[(df['Misspelling or special character'].isin(selected_categories)) &
                         (df["Duplicate with 's'"].isin(duplicate_s))]
    elif selected_categories:
        filtered_df = df[df['Misspelling or special character'].isin(selected_categories)]
    elif duplicate_s:
        filtered_df = df[df["Duplicate with 's'"].isin(duplicate_s)]
    else:
        filtered_df = df

    csv_out = filtered_df.to_csv(index=False)
    st.download_button('Download Table as CSV', csv_out, file_name='output.csv', mime='text/csv')

    st.caption("Preview (first 1000 rows):")
    st.table(filtered_df.head(1000))
