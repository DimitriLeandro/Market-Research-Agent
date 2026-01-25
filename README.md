# Market Research Agent

This repository contains a personal Python project that uses **Google Gemini models** to perform **LLM-driven web-based research and qualitative analysis of Brazilian publicly traded stocks**, such as **ITUB3, VALE3, PETR4, BBAS3**, and others.

The core idea of the project is to automatically research the internet for **recent news** related to each company and to infer the **general market sentiment** around those events. The system performs a structured research pass for each asset, followed by additional LLM prompts that summarize the most relevant information; synthesize the overall narrative around the company; and classify the expected price trend into qualitative categories.

Instead of email notifications, the final outputs are sent directly to **Google Chat**, which is the primary communication tool used in the company I work in, making things very easy in my daily workflow.

The project also persists daily results as **markdown files**, building a chronological history of analyses. Before sending any new message, a final comparison step evaluates whether the current day’s output is meaningfully different from the previous day’s result, reducing noise and avoiding unnecessary notifications.

The script is designed to run locally on **Ubuntu 22.04 LTS**, executed automatically as part of the system startup via shell configuration for my personal use case.