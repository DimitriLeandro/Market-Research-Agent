import json
import subprocess
from datetime import date
from pathlib import Path
from google import genai
from google.genai import types
from joblib import Parallel, delayed
from tickers_list import tickers_list

CREDENTIALS_PATH = Path("../credentials/credentials.json")
RESEARCH_PROMPT_PATH = Path("../prompts/stocks_prompt.md")
COMPARISON_PROMPT_PATH = Path("../prompts/comparison_prompt.md")
RESULTS_BASE_DIR = Path("..") / "results"

REPORT_HEADER_TEMPLATE = "# Report {}"
REPORT_SECTION_SEPARATOR = "\n"
GIT_COMMIT_MESSAGE_TEMPLATE = "docs: report of {} (auto commit)"

def _run_research_for_ticker(client, search_config, ticker_code, prompt_template, output_directory, date_string):
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt_template.format(ticker_code=ticker_code),
        config=search_config,
    )
    
    output_file = output_directory / f"{ticker_code}_{date_string}.md"

    # Fix: Handle cases where response.text is None (e.g., Safety Blocks)
    content_to_write = response.text if response.text else f"Error: No content generated for {ticker_code} (Likely Safety Filter Block)."

    with output_file.open("w", encoding="utf-8") as f:
        f.write(content_to_write)

def perform_initial_research(client, search_config, tickers, prompt_template, output_directory, date_string):
    Parallel(n_jobs=-1, prefer="threads")(
        delayed(_run_research_for_ticker)(
            client, 
            search_config, 
            ticker_code, 
            prompt_template, 
            output_directory, 
            date_string
        ) 
        for ticker_code in tickers
    )

def _run_comparison_for_ticker(client, ticker_code, prompt_template, today_dir, previous_dir, date_string):
    current_file = today_dir / f"{ticker_code}_{date_string}.md"

    if not current_file.exists():
        return None

    current_result = current_file.read_text(encoding="utf-8")
    
    previous_file = previous_dir / f"{ticker_code}_{previous_dir.name}.md"
    previous_result = 'NOT FOUND'
    
    if previous_file.exists():
        previous_result = previous_file.read_text(encoding="utf-8")

    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt_template.format(
            previous_result=previous_result,
            current_result=current_result
        )
    )

    # Fix: Handle cases where response.text is None
    text_content = response.text if response.text else "Error: No comparison generated."

    return "## " + ticker_code + "\n\n" + text_content.replace("\n---\n", "")

def generate_comparison_report(client, tickers, prompt_template, base_directory, date_string):
    today_dir = base_directory / date_string
    
    previous_dirs = sorted([d for d in base_directory.iterdir() if d.is_dir() and d.name != date_string])
    
    if not previous_dirs:
        return

    previous_dir = previous_dirs[-1]

    results = Parallel(n_jobs=-1, prefer="threads")(
        delayed(_run_comparison_for_ticker)(
            client,
            ticker_code,
            prompt_template,
            today_dir,
            previous_dir,
            date_string
        )
        for ticker_code in tickers
    )

    responses = [res for res in results if res is not None]

    final_report_content = REPORT_HEADER_TEMPLATE.format(date_string) + REPORT_SECTION_SEPARATOR.join(responses)
    output_file = today_dir / f"final_report_{date_string}.md"

    with output_file.open("w", encoding="utf-8") as f:
        f.write(final_report_content)

def push_to_github(date_string):
    subprocess.run(["git", "add", "-A"])
    subprocess.run(["git", "commit", "-m", GIT_COMMIT_MESSAGE_TEMPLATE.format(date_string)])
    subprocess.run(["git", "push"])

def main():
    with CREDENTIALS_PATH.open("r", encoding="utf-8") as file:
        credentials = json.load(file)

    gemini_api_key = credentials["gemini_api_key"]
    
    with RESEARCH_PROMPT_PATH.open("r", encoding="utf-8") as file:
        research_prompt = file.read()

    with COMPARISON_PROMPT_PATH.open("r", encoding="utf-8") as file:
        comparison_prompt = file.read()

    today_str = date.today().strftime("%Y_%m_%d")
    results_dir = RESULTS_BASE_DIR / today_str
    results_dir.mkdir(parents=True, exist_ok=True)

    client = genai.Client(
        api_key=gemini_api_key
    )

    generation_config = types.GenerateContentConfig(
        tools=[
            types.Tool(
                google_search=types.GoogleSearch()
            )
        ]
    )

    perform_initial_research(
        client, 
        generation_config, 
        tickers_list, 
        research_prompt, 
        results_dir, 
        today_str
    )

    generate_comparison_report(
        client, 
        tickers_list, 
        comparison_prompt, 
        RESULTS_BASE_DIR, 
        today_str
    )

    push_to_github(today_str)

if __name__ == "__main__":
    main()