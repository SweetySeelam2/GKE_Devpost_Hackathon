# 🧠 AI Agent for Online Boutique – GKE Hackathon

---

**🔗 Hosted Demo**
- Project URL: https://34-54-178-42.nip.io  
- API Routes:
  - `/api/recommend/demo-user`
  - `/api/health/details`

## 📘 Description

**📖 Overview**

This project extends Google’s Online Boutique microservices demo application with a new AI Agent microservice deployed on Google Kubernetes Engine (GKE). Instead of modifying existing services, the agent acts as an external intelligent layer that observes, queries, and enhances the application’s behavior — providing personalized recommendations, diagnostics, and AI reasoning. I deployed a new FastAPI service on GKE that enhances the app with **AI-powered product recommendations**.

---

## ✨ Features & Functionality

**Recommendation Engine:**

- API: /api/recommend/{user_id} returns top 3 products.

- Pulls data from the Online Boutique frontend (/api/products) or scrapes HTML when JSON APIs aren’t available.

- Normalizes price, images, and product metadata into a clean JSON response.

**Health Diagnostics:**

- API: /api/health/details actively checks the frontend and catalog services.

- Reports status codes, connection errors, or skipped probes for better observability.

**LLM Extension with Gemini:**

- Prepared for Google Generative AI (Gemini) integration.

- Can explain recommendations or re-rank results via reasoning prompts.

**Scraping Fallback:**

Even when APIs fail, the agent parses “Hot Products” directly from the frontend HTML, ensuring robustness.

---

## 🛠️ Technologies Used

- GKE (Google Kubernetes Engine): Core platform to deploy agent as a containerized service alongside Online Boutique.

- FastAPI + Uvicorn: Lightweight Python-based web framework powering the AI Agent.

- Cloud Build + Artifact Registry: CI/CD pipeline to build, push, and roll out new container versions (kubectl set image ...).

- Google Generative AI SDK (Gemini): Pre-integrated to allow LLM-based reasoning and explanations.

- Agent Development Kit (ADK): (Optional) Could provide a richer framework for agent orchestration in production.

- Model Context Protocol (MCP): (Optional) Enabling structured multi-service communication (e.g., wrapping gRPC catalog service).

- Agent2Agent (A2A): (Optional) Demonstrates how multiple external AI agents could coordinate workflows (recommendations + fraud checks).

---

## 📊 Data Sources Used

- Frontend JSON API (/api/products) — structured product data when available.

- Frontend HTML Scrape — fallback path to parse hot product cards.

- Catalog Service (gRPC) — noted but not directly consumable via REST; readiness handled.

- Environment Config (FRONTEND_URL, CATALOG_URL) — ensures portability across environments.

---

## 🧩 Findings & Learnings

**Ingress & Path Handling:**

- Proper configuration of /api routing in boutique-ingress was critical.

- Misaligned root paths initially caused 404/502 errors — solved via correct prefix and uvicorn args.


**gRPC vs REST:**

- The catalog service runs on gRPC, which made direct REST probing unreliable.

- Documented and explicitly skipped catalog readiness in diagnostics.


**Resilience via Scraping:**

- Relying only on JSON APIs was fragile; scraping fallback ensured consistent recommendations.

- Regex parsing with caching reduced load and improved response times.


**Gemini Integration Readiness:**

- Integrated google-generativeai SDK so the agent can explain recommendations.

- Could be extended to rank products by semantic similarity or user context.


**Hackathon-Specific Learnings:**

- Time saved by isolating intelligence in a new container, instead of touching core services.

- Debugging ingress health probes was the most time-consuming but rewarding step.

---

## What it does
- Scrapes or queries the Online Boutique frontend/catalog to suggest top products.
- Provides a clean **`/api/recommend/{user}`** endpoint for intelligent recommendations.
- Adds a **health diagnostics API** at `/api/health/details`.
- (Optional) Integrates **Gemini** (`google-generativeai`) to re-rank recommendations or explain results.

---

## 📊 Architecture Diagram

flowchart LR
  User((User)) --> Ingress
  Ingress -->|/| Frontend[Online Boutique Frontend]
  Ingress -->|/api| AI[AI Agent (FastAPI + Gemini) on GKE]
  AI -->|HTTP scrape /api/products| Frontend
  AI -->|env vars| CFG[(Config: FRONTEND_URL, CATALOG_URL)]
  AI -. optional .->|gRPC via shim| Catalog[(productcatalogservice:3550)]
  AI -->|JSON| Response[(Top-3 recommendations)]
  subgraph GKE
    Ingress
    Frontend
    AI
    Catalog
  end

---

## 🚀 Deployment

**Build and push:**
```bash
gcloud builds submit --tag us-central1-docker.pkg.dev/PROJECT/ai-agents/ai-agent:v14
```

**Update Deployment:**
```bash
kubectl set image deploy/ai-agent ai-agent=us-central1-docker.pkg.dev/PROJECT/ai-agents/ai-agent:v14
kubectl rollout status deploy/ai-agent
```

**Access at Ingress URL.**

---

## 📖 Learnings

- Handling gRPC vs REST differences in catalog service.

- Robustness: scraping fallback ensures results even without JSON APIs.

- Ingress path matching and root-path issues were key debugging points.

- Gemini can enhance recommendations beyond static scraping.

---

## Testing Instructions
**1. Open the hosted Online Boutique frontend:**
   https://34-54-178-42.nip.io  

**2. Test the AI Agent recommendation endpoint:**  
curl -sS https://34-54-178-42.nip.io/api/recommend/demo-user | jq .
→ Returns a JSON object with 3 recommended products (id, name, price, picture).

**3. Test diagnostics endpoint:**  
curl -sS https://34-54-178-42.nip.io/api/health/details | jq .
→ Shows component health (frontend OK, catalog skipped).

**4. If local testing:** 
kubectl port-forward svc/ai-agent 8081:80
curl -sS http://127.0.0.1:8081/api/recommend/demo-user
curl -sS http://127.0.0.1:8081/api/health/details

---

## 📝 Gemini CLI Prompt Support - Ask questions related to the commands ran for this project and the AI will answer those instantly.

**Example Prompts**

**1. Generate crisp demo script**
gemini "Explain about the recommend user-demo and api/health/details code ran for my GKE Hackathon project: AI Agent microservice for Online Boutique. URLs: https://34-54-178-42.nip.io, /api/recommend/demo-user, /api/health/details"

**2. Debug rollout issues**
kubectl rollout status deploy/ai-agent | gemini "Explain this output and what I should check next if pods don’t update."

---

## Project Links

Video Demo: https://youtu.be/DuM6I7Rh_no

---

## 👩‍💻 Author

**Sweety Seelam**


Business Analyst & Aspiring Data Scientist
