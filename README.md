# AETHER Realty — AI Lead Qualifier

An AI-powered lead qualification agent for Lake Region realtors. Built with the AETHER WIT Engine + Gemini AI.

## What It Does

Your AI assistant sits on your website and has a natural conversation with every visitor — asking what they're looking for, their timeline, their budget — and only sends you the qualified leads via email.

**Live Demo:** [aether-realty-demo.netlify.app](https://aether-realty-demo.netlify.app)

## Deploy Your Own

### Frontend (Netlify)
[![Deploy to Netlify](https://www.netlify.com/img/deploy/button.svg)](https://app.netlify.com/start/deploy?repository=https://github.com/poinsettiaclg-gif/aether-realty)

### Backend (Render)
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/poinsettiaclg-gif/aether-realty)

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Get one at [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| `REALTOR_EMAIL` | No | Email to receive qualified lead notifications |
| `SENDGRID_API_KEY` | No | For production email delivery |
| `FRONTEND_URL` | No | Your frontend URL (for CORS) |

## Tech Stack

- **AI Engine:** AETHER WIT (Weighted Intent Tokens) + Gemini 2.5 Pro
- **Backend:** FastAPI + SQLite
- **Frontend:** Vanilla HTML/CSS/JS
- **Notifications:** SendGrid / SMTP

## Architecture

```
Buyer visits site → AI Chat Widget → Natural conversation
                                          ↓
                                    AETHER WIT Engine extracts:
                                    • Intent (buying/selling)
                                    • Timeline
                                    • Budget
                                    • Contact info
                                          ↓
                                    Lead Qualified? → Email to Realtor
```

## License

MIT
