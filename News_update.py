from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
from datetime import datetime
import os
import re

today = f"{datetime.now().month}/{datetime.now().day}/{datetime.now().year}"
print(today)
news = []

ferro_username = "bekkas"
ferro_password = "dalimov1981"

options = webdriver.ChromeOptions()

profile_path = os.path.join(os.getcwd(), "ferro_chrome_profile")
options.add_argument(f"user-data-dir={profile_path}")
options.add_experimental_option("detach", True)

driver = webdriver.Chrome(options=options)

driver.get("https://www.ferroalloynet.com/member/signin.html")   # or the actual login page

wait = WebDriverWait(driver, 2)

if "signin" in driver.current_url:
    print("Need login")

    driver.find_element(By.ID, "TextBox_MemberID").send_keys(ferro_username)
    driver.find_element(By.ID, "TextBox_Password").send_keys(ferro_password)
    driver.find_element(By.ID, "Button_Signin").click()

    time.sleep(3)

else:
    print("Already logged in")

driver.get("https://www.ferroalloynet.com/")

wait.until(
    EC.presence_of_element_located((By.TAG_NAME, "body"))
)

time.sleep(2)

# click Vanadium menu
vanadium_link = wait.until(
    EC.element_to_be_clickable((By.LINK_TEXT, "Vanadium"))
)

vanadium_link.click()

time.sleep(3)

MAX_NEWS = 10

article_bodies = driver.find_elements(By.CLASS_NAME, "Article_Body")[:3]

exclude = "Vanadium Price Chart"

for body in article_bodies:

    titles = body.find_elements(By.CLASS_NAME, "Channel_Category_Title")
    lists = body.find_elements(By.CLASS_NAME, "Channel_Category_List")

    for title_cell, list_cell in zip(titles, lists):

        category = title_cell.find_element(By.TAG_NAME, "a").text
        category = category.replace("» More", "").replace("\n", " ").strip()

        if category == exclude:
            continue

        for p in list_cell.find_elements(By.TAG_NAME, "p"):

            spans = p.find_elements(By.XPATH, ".//span[contains(@class,'adate_')]")
            if not spans:
                continue

            if spans[0].get_attribute("title").strip() == today:

                link = p.find_element(By.TAG_NAME, "a")

                news.append({
                    "category": category,
                    "title": link.get_attribute("title"),
                    "url": link.get_attribute("href")
                })

                if len(news) == MAX_NEWS:
                    break

        if len(news) == MAX_NEWS:
            break

    if len(news) == MAX_NEWS:
        break


print(news)

def get_article_content(driver, url):

    driver.get(url)

    wait.until(
        EC.presence_of_element_located(
            (By.CSS_SELECTOR, "td.ArticleViewContent")
        )
    )

    article = driver.find_element(
        By.CSS_SELECTOR,
        "td.ArticleViewContent"
    )

    # ==================================================
    # 1. CHECK FOR A REAL TABLE
    # ==================================================

    tables = article.find_elements(By.TAG_NAME, "table")

    for table in tables:

        rows = table.find_elements(By.TAG_NAME, "tr")

        table_data = []

        for row in rows:

            cells = row.find_elements(
                By.XPATH,
                "./th | ./td"
            )

            row_data = []

            for cell in cells:

                cell_text = cell.get_attribute("textContent")

                if not cell_text:
                    continue

                cell_text = re.sub(
                    r"\s+",
                    " ",
                    cell_text
                ).strip()

                if cell_text:
                    row_data.append(cell_text)

            if row_data:
                table_data.append(row_data)

        # Only consider it a useful table if it has
        # at least 3 rows and at least 2 columns
        if len(table_data) >= 3:

            max_columns = max(
                len(row)
                for row in table_data
            )

            if max_columns >= 2:

                return {
                    "type": "table",
                    "content": table_data[:3]
                }


    # ==================================================
    # 2. TEXT ARTICLE
    # ==================================================

    # FerroAlloyNet puts the article paragraphs
    # directly inside ArticleViewContent as <div> elements.

    paragraphs = article.find_elements(
        By.XPATH,
        "./div"
    )

    text_parts = []

    for paragraph in paragraphs:

        # Get raw text rather than relying on .text
        text = paragraph.get_attribute(
            "textContent"
        )

        if not text:
            continue

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        # Skip empty spacer divs
        if not text:
            continue

        text_parts.append(text)


    # ==================================================
    # 3. IF DIRECT DIVS WERE NOT FOUND
    #    TRY ALL DIVS AS FALLBACK
    # ==================================================

    if not text_parts:

        paragraphs = article.find_elements(
            By.TAG_NAME,
            "div"
        )

        for paragraph in paragraphs:

            # Skip anything inside a table
            if paragraph.find_elements(
                By.XPATH,
                "ancestor::table"
            ):
                continue

            text = paragraph.get_attribute(
                "textContent"
            )

            if not text:
                continue

            text = re.sub(
                r"\s+",
                " ",
                text
            ).strip()

            if not text:
                continue

            text_parts.append(text)

    # ==================================================
    # 4. CREATE TEXT SUMMARY
    # ==================================================

    if text_parts:

        # Keep paragraphs separate
        full_text = " ".join(text_parts)

        # Clean whitespace
        full_text = re.sub(r"\s+", " ", full_text).strip()

        # --------------------------------------------------
        # Split into sentences
        # Handles ., !, ? followed by a space
        # --------------------------------------------------

        sentences = re.split(
            r'(?<=[.!?])\s+',
            full_text
        )

        sentences = [
            sentence.strip()
            for sentence in sentences
            if sentence.strip()
        ]

        # --------------------------------------------------
        # Take ONLY first 3 sentences
        # --------------------------------------------------

        summary_sentences = sentences[:2]

        summary = " ".join(summary_sentences)

        # --------------------------------------------------
        # If sentence detection fails:
        # Limit to approximately 3 sentences/short portion
        # --------------------------------------------------

        if not summary_sentences and full_text:
            summary = full_text

        if summary:
            return {
                "type": "text",
                "content": summary
            }
    # ==================================================
    # 5. NOTHING FOUND
    # ==================================================

    return None
# ==================================================
# GET CONTENT FROM NEWS
# ==================================================

print("\nGetting article content...")

valid_news = []

for item in news:

    print("\n----------------------------------------")
    print("Title:", item["title"])

    try:

        result = get_article_content(
            driver,
            item["url"]
        )

        if result is None:

            print("No usable text or table. Skipping.")
            continue


        # ------------------------------------------
        # NORMAL TEXT ARTICLE
        # ------------------------------------------

        if result["type"] == "text":

            item["content_type"] = "text"
            item["summary"] = result["content"]

            print("Type: TEXT")
            print("Summary:", item["summary"])


        # ------------------------------------------
        # TABLE ARTICLE
        # ------------------------------------------

        elif result["type"] == "table":

            item["content_type"] = "table"
            item["table"] = result["content"]

            print("Type: TABLE")
            print("First 3 rows:")

            for row in item["table"]:
                print(row)


        valid_news.append(item)


    except Exception as e:

        print("ERROR:", e)


# Replace news with only usable articles
news = valid_news[:MAX_NEWS]


# ==================================================
# FINAL RESULT
# ==================================================

print("\n\nFINAL NEWS")
print("========================================")

for item in news:

    print("\nCategory:", item["category"])
    print("Title:", item["title"])
    print("URL:", item["url"])
    print("Type:", item["content_type"])

    if item["content_type"] == "text":

        print("Summary:", item["summary"])

    elif item["content_type"] == "table":

        print("Table:")

        for row in item["table"]:
            print(row)

def capitalize_title(title):

    words = title.split()

    # Small words that normally stay lowercase
    small_words = {
        "a", "an", "the",
        "and", "or", "but",
        "for", "nor",
        "on", "at", "to",
        "by", "in", "of",
        "with", "from"
    }

    result = []

    for i, word in enumerate(words):

        # Always capitalize first word
        if i == 0:
            result.append(
                word[0].upper() + word[1:]
            )
            continue

        # Preserve words that already contain uppercase letters
        if any(char.isupper() for char in word):
            result.append(word)
            continue

        # Keep small connecting words lowercase
        if word.lower() in small_words:
            result.append(word.lower())
            continue

        # Capitalize normal words
        result.append(
            word[0].upper() + word[1:]
        )

    return " ".join(result)

vanadium_login = "tamirbatsuri@gmail.com"
vanadium_password = "VanadiumPrice@2024"

driver.get("https://vanadiumprice.com/wp-login.php")

time.sleep(2)

driver.find_element(
    By.ID,
    "user_login"
).send_keys(vanadium_login)


driver.find_element(
    By.ID,
    "user_pass"
).send_keys(vanadium_password)


driver.find_element(
    By.ID,
    "wp-submit"
).click()


time.sleep(2)

driver.get("https://vanadiumprice.com/wp-admin/post-new.php")

# ============================================================
# POST NEWS TO WORDPRESS
# ============================================================

wait = WebDriverWait(driver, 10)


def table_to_html(table_data):

    html = '<table style="width:100%; border-collapse:collapse;">'

    # Header
    html += "<thead><tr>"

    for cell in table_data[0]:
        html += (
            '<th style="border:1px solid #ddd; padding:8px;">'
            + cell +
            '</th>'
        )

    html += "</tr></thead>"

    # Data rows
    html += "<tbody>"

    for row in table_data[1:]:

        html += "<tr>"

        for cell in row:
            html += (
                '<td style="border:1px solid #ddd; padding:8px;">'
                + cell +
                '</td>'
            )

        html += "</tr>"

    html += "</tbody></table>"

    return html


for item in news:

    # print("\n========================================")
    # print("Posting:", item["title"])
    # print("CONTENT TYPE:", item["content_type"])

    try:

        # --------------------------------------------------
        # OPEN NEW POST
        # --------------------------------------------------

        driver.get(
            "https://vanadiumprice.com/wp-admin/post-new.php"
        )

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

        title_box = wait.until(
            EC.presence_of_element_located(
                (By.ID, "title")
            )
        )

        title = capitalize_title(item["title"])

        # print("Title:", title)

        title_box.clear()
        title_box.send_keys(title)

        # --------------------------------------------------
        # CREATE BODY
        # --------------------------------------------------

        if item["content_type"] == "text":

            # print("Creating TEXT body")

            body = (
                "<p>" + item["summary"] + "</p>"
                "<p><strong>For more information, please visit:</strong> "
                '<a href="' + item["url"] + '" target="_blank">'
                + item["url"] +
                "</a></p>"
            )

        elif item["content_type"] == "table":

            # print("Creating TABLE body")

            body = table_to_html(item["table"])

            body += (
                "<p><strong>For more information, please visit:</strong> "
                '<a href="' + item["url"] + '" target="_blank">'
                + item["url"] +
                "</a></p>"
            )

        else:

            print("UNKNOWN CONTENT TYPE — SKIPPING")
            continue

        # print("Body created successfully")

        # --------------------------------------------------
        # WAIT FOR EDITOR
        # --------------------------------------------------

        wait.until(
            EC.presence_of_element_located(
                (By.ID, "content_ifr")
            )
        )

        time.sleep(1)

        # --------------------------------------------------
        # PUT CONTENT INTO TINYMCE
        # --------------------------------------------------

        driver.execute_script(
            """
            if (typeof tinymce !== 'undefined') {

                var editor = tinymce.get('content');

                if (editor) {

                    editor.setContent(arguments[0]);
                    editor.save();

                } else {

                    throw new Error("TinyMCE editor not found");

                }

            } else {

                throw new Error("TinyMCE not loaded");

            }
            """,
            body
        )

        # print("Content inserted")

        time.sleep(1)

        # --------------------------------------------------
        # SELECT VANADIUM NEWS CATEGORY
        # --------------------------------------------------

        category_checkbox = wait.until(
            EC.presence_of_element_located(
                (By.ID, "in-category-11-2")
            )
        )

        if not category_checkbox.is_selected():

            driver.execute_script(
                "arguments[0].click();",
                category_checkbox
            )

        # print("Vanadium News category selected")

        # --------------------------------------------------
        # SAVE AS DRAFT
        # --------------------------------------------------

        publish = wait.until(
            EC.element_to_be_clickable(
                (By.ID, "publish")
            )
        )

        publish.click()

        time.sleep(3)

        # ==================================================
        # COPY-READY NEWS OUTPUT
        # ==================================================

        print("\n\n")
        print("=" * 80)
        print("COPY-READY NEWS")
        print("=" * 80)

        for item in news:

            title = capitalize_title(item["title"])

            print("\n")
            print(title)
            print()

            if item["content_type"] == "text":

                print(item["summary"])
                print()

                print("For more information: " + item["url"])

            elif item["content_type"] == "table":

                # Print table rows
                for row in item["table"]:
                    print(" | ".join(row))

                print()
                print("For more information: " + item["url"])

            print()
            print("-" * 80)


    except Exception as e:

        print("\n!!!!!!!! POSTING ERROR !!!!!!!!")
        print("Title:", item["title"])
        print("Type:", item["content_type"])
        print("URL:", item["url"])
        print("ERROR:", repr(e))

        # Don't silently continue
        continue