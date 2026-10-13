# HW5 — AI Prompts Log

This is a log of the prompts I typed to my AI coding assistant (vibe coder) while working on HW5, Campus Customs Multi-Agent Operations: an MCP server, a FastAPI backend with a multi-agent team (Boss, Inventory, Accounting, Facilities, Customer Service), and a React dashboard. Each problem gets its own section with the prompts I typed in my own words.

---

## Problem 1: Setup and AI Prompts Log

**Prompt:**
> This is going to be Hw 5

**Prompt:**
> alright here's the game, I'm going to give you the scenario and then we're going to go through 11 problems together

**Prompt:**
> (shared the Campus Customs scenario and the `campus_customs.db` file) ok let's get it baby

**Prompt:**
> yes gpt-6-luna

**Prompt:**
> Create AI_prompts.md at the start of the assignment and keep it updated as i work. This file is the log of what I typed to my vibe coder. I describe each problem to my vibe coder in my own words. Put one section for each problem. Each section must include the following: - the problem number and title - at least one prompt that I typed, in my own words as much as possible - one follow-up prompt if I needed it (and one sentence on what was lacking after the first)

**Follow-up:**
> ok here's problem 1, let's start logging including this messsage : Create AI_prompts.md at the start of the assignment and keep it updated as i work. ...

*What was lacking after the first prompt:* The log file hadn't been created yet, so I clarified that this was Problem 1 and that the logging should start now and include this message.

---

## Problem 2: Explore the Database and Start the Harness

**Prompt:**
> Open data/campus_customs.db and look through every table and its fields. Copy the original file to data/campus_customs_new.db — later problems update that working copy. Study the three open tickets so you see how they link to other tables. Start output/harness.md . For each table, list the fields and one short line on why that tables matters for the agents. I will keep growing this harness file in later problems.

---

## Problem 3: MCP Server with Three Tools

**Prompt:**
> Problem 3: Write an MCP server in mcp_server/ using FastMCP. It will talk to data/campus_customs_new.db. You do not need to connect or run it in this problem. Every agent in this homework uses the tools in this MCP server. You will add more tools to it later; for now write three tools you know you will need for the tickets in the database. I want you to think about what the best three tools you can conjure up thinking about the task at hand. Keep the names clear. Never invent any data, only use information in the database. Keep the names clear. Never invent any data, only use information in the database!! important!! In output/harness.md , list each of your three MCP tools. For every tool include: which table it reads, which ticket it helps unlock (101, 102, or 103) and for one sentence on why that tool is the right for that ticket, you must log your logic on why that tool is the right one. Also add a short mcp_server/readme.md file that explains what the MCP server is for, which database file it uses and the three tools it has. ok rip it

---

## Problem 4: Connect the MCP Server to the Vibe Coder

**Prompt:**
> Problem 4: In your vibe coder (Claude Code, Codex, or Cursor), add your MCP server to this project so the vibe coder can call the tools. Save the connection JSON text in .mcp.json at the project root (or however your vibe coder saves local MCP server lists). You just need to figure it out yourself for that. With your vibe coder connected, test each of the three mcp tools. Save the evidence in output/mcp_smoke.json For every tool include: the prompt you asked the vibe coder , the tool name, and the tool output (data/campus_customs_new.db) . OK rip it

**Follow-up:**
> ok just do whatever you said, I dont' want to type it out you have my permissio to do the to finish: part yourself

*What was lacking after the first prompt:* The .mcp.json was written, but the session had started in hw3, so Claude Code hadn't loaded the campus-customs server yet. After I reopened the session in hw5 and approved the server, I let the vibe coder run the three smoke-test prompts itself.

---

## Problem 5: Build the Multi-Agent Team

**Prompt:**
> Problem 5: rip it. Build the agentic team for Campus Customs using PydanticAl: Boss, Inventory, Accounting, Facilities, and Customer Service. Include prompts, models, and agent loops so they can delegate work to each other with full connectivity. Put the agent prompts in backend/prompts/ — one file per agent. Put data types in backend/models. py, and the agent files under backend/ (your layout can vary as long as the five roles are clear). Use my PORTKEY_API_KEY and only gpt-6-Luna tor every agent. Write each prompt in your own words with the shop rules that agent needs. More detailed prompts that cover all aspects of an agent's work and scope score higher than a short generic prompt. As such, I want you to think of this a long time and after that I want you to write a detailed and eloquent prompt. Rip it bro go go go for that. Add any tools the agents need to my MCP server so they can work on the open tickets. Shop facts come from the MCP server over data/campus_customs_new.db - do not invent a second shop-tools layer that bypasses MCP. Wire the agents so they append to output/audit_trail.json as they run: for each agent-loop step, record enough to audit later. Append to this file - do not wipe it each run. In output/harness.md , list each agent and each MCP tool (including the ones you add in this problem) along with which table the tool uses. Also add a short safety section : the guardians a real business would want agents touch real customers and real money, plus limits that keep token use in check, very important!!! Update mcp_server/readme.md so the tool list matches what you have now. alright brah rip it!!

---

## Problem 6: Expected Plan Page (desk_tickets.html)

**Prompt:**
> Problem 6: Before you wire the backend, write down what you expect the team to do on each open ticket. Build output/desk_tickets.html — a page you can double-click with one tab per ticket (101, 102, and 103). Also add empty Cash and Reflection tabs for later problems (leave them blank or with a short "coming later" note for now). On each ticket tab, fill an Expected section only (leave room for an Actual section you will fill after you run the agents). For each ticket's Expected section, write in your own words (come up with it and properly record it below be thoughtful): Who the Boss should call first, and why; All the agent delegations you expect - not "Boss calls everyone"; Which MCP tools you expect that run to use. Plans that send every specialist on every ticket score low. You will compare this plan to what actually happens when your agents resolve the three tickets. OK rip it.

---

## Problem 7: FastAPI Backend Routes

**Prompt:**
> Problem 7: My React frontend dashboard (the next problem) needs a backend it can call. In backend/main.py. use FastAPl and add routes that do the following: Return the three tickets and whether each is open or resolved; Take a ticket id and run your agent team on that ticket; Return recent agent events — what each agent said and which tools they used - so the board can refresh; Approve a payment or purchase after a human clicks approve (agents only prepare the pay; this route is what actually changes cash); Return the current checking balance from cash_accounts; Reset the database to the original values when you want to try a fresh run

**Follow-up:**
> (re-sent the same problem text with the startup instructions) From the backend/ folder, start the server with : uvicorn main:app --reload --port 8000. This turns on my backed at http://localhost:8000 so the front end dashboard can call those routes. In output/harness.md list each route in one line (what URL/ what it does). OK RIP IT GOGOGOOGOG.

*What was lacking after the first prompt:* My first message got cut off before I said how the server is started (from backend/ with `uvicorn main:app`) and that the routes needed to be listed in harness.md, so I re-sent it with those details.

---

## Problem 8: React Dashboard (Shoreline Desk)

**Prompt:**
> Problem 8: Build the frontend dashboard in frontend/ with React + Vite + TypeScript. The page should call the routes you built in Problem 7. At minimum the board should: List all three tickets; Let you pick one ticket and start the agent team on it; Show each agent and what they are saying / doing while the ticket runs; Mark a ticket resolved when the run finishes; Show a short summary of what each agent did on that ticket; Let a human approve a pay or purchase when asked; Show the checking balance (it should drop after an approved pay). Make the dashboard look good. Be creative with the layout and feel - this is a real desk people would want to sit at, so put thought into how it

**Follow-up:**
> (re-sent the full problem with more direction) ... please feel free to add anything else other than above bullet points you think will help and any that will make your life easier. Make the dashboard look good. Be creative with the layout and feel - this is a real desk people would want to sit at, so put thought into how it. Find some popular and professional looking dashboards you can reference and if it's highly rated go ahead and go witha very similar theme as that. Think of something warm too, it's about making real life people feel better and more chill. We want it to be welcoming!! Even a little surf theme or beach theme like a tropical island vacation background theme would be sick!! Tell the front end to talk to your backend at http://localhost:8000 . On the backend allow the Vite page origin (usually http://localhost:5173) so the browser is allowed to call those routes. Start the board with: npm run dev. Write output/design.md with what you chose for the dashboard look (layout, how agents read differently, how resolved tickets and cash show up) and why - including the creative choices that make it feel special and something humans would actually enjoy using. ok rip it!!!

*What was lacking after the first prompt:* My first message got cut off mid-sentence and didn't give the look I wanted (warm, welcoming, beach/tropical, based on highly rated dashboards), the backend URL and CORS origin, the `npm run dev` start command, or the design.md write-up, so I re-sent it with all of that.

---

## Problem 9: Full Run, Expected vs Actual, Cash, and Final Harness

**Prompt:**
> Problem 9: Before testing the agents on a full run over the three tickets, reset the working database data/campus_customs_new.db again so you start clean. Note the starting checking balance. Then run all three tickets on the board (101, 102, 103) until each is resolved. Open output/desk_tickets.html from Problem 6. On each ticket tab, fill the Actual section from this run: which agents worked, what they delegated, and which tools they used. Keep your Expected section so you can compare the two. It's an important log. On the Cash tab of the same output/desk_tickets.html, itemize the money: Starting checking balance (after the reset); For each ticket: how cash changed when that ticket resolved, and why (which pay / purchase, dollar amount); Ending checking balance — it must match cash_accounts in the working database. Wrong cash math loses points even if the board shows every ticket resolved. Also save: output/resolved_tickets.json — for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals; output/resolved_board.htm1 — a page you can double-click with a screenshot of your React board for each resolved ticket (101, 102, and 103). Append real runs to output/audit_trail.json. Finish output/harness.md so it covers tables, MCP tools, the five agents, API routes, the dashboard, and safety rules. It's a big ask but you got this, rip it brah!!

**Follow-up:**
> (answering the vibe coder's two questions) Approvals: "You approve, signed with my name". Port 8000: "Yes, stop the old HW3 servers".

*What was lacking after the first prompt:* The problem didn't say who should click Approve on the payments or what to do about the old HW3 server holding port 8000, so I chose to have the vibe coder approve in the dashboard signed with my name, and to stop the old servers so the backend ran on 8000.

---

## Problem 10: Reflection

**Prompt:**
> Problem 10: Ok so given that problem 10 will be the following you can't run it entirely since I have to write a reflection, with these main things in mind below can you give me an idea of what I can write for each of these and I will take those ideas and rip it into my thoughts and my wave and vibe. Big surfer energy from LA, which I am! Ok with that in mind the problem 10 objective: Open output/desk_tickets.html and fill the Reflection tab. Answer in your own vibe, and be detailed and thorough: How would you evaluate the performance of the agents on each ticket and why? For each ticket, how did Actual compare to the Expected plan you wrote earlier? What would have been simpler as one agent with tools - and why? Describe three new problems Campus Customs might face that this agent team could solve with the tools you built. Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them. Tie every answer to this app and the three tickets you ran - use the ticket tabs and Cash tab on the same page as your evidence. Generic AI essays without Campus Customs details will score low.

**Follow-up:**
> reflection: For some reason on this project I went with a surfer vibe with my ai. Maybe because it's the fact that I grew up surfing near a beach. For that reason my interpretation of my own vibe is using waves as a metaphor. For ticket 101, it was pretty decent but not great. A wave that was worth it but not truly memorable. ... For ticket 102, this was a wave of the day kind of situation. ... Ticket 103 was the worst ticket. It was as if you tried to catch the wave but didn't even catch it. ... (plus my three could-solve and three could-not-solve problems)

*What was lacking after the first prompt:* The first prompt asked only for ideas, so this follow-up gave my actual reflection, written in my own surfer voice, to put into the Reflection tab of desk_tickets.html.

---

## Problem 11: Public GitHub Repo

**Prompt:**
> Problem 11: Push your code to a public GitHub repository so graders can clone it. Submit the repo URL to Canvas, I myself will do this canvas part but give me url and also you must put it in output/github_url.txt Do not push your real .env to the GitHub repo. Do include both database files under data/ (the original and your working copy) so graders can run your app easily. Expected file layout: (pasted the hw5/ file tree)

**Follow-up:**
> Readme should explain: copy original DB to the working copy when you need a clean run, start MCP server, start FastAPI backen, start the react board, reset the DB before a full three-ticket run.

**Follow-up:**
> this is expected layout cleanr might help (sent a screenshot of the clean file tree)

*What was lacking after the first prompt:* My first messages got cut off and the pasted file tree was messy, so I added what the README had to explain and re-sent the layout as a clean screenshot.

---
