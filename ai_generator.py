"""
ai_generator.py — Generates personalized DM messages via OpenRouter.
"""
import json
import requests
from loguru import logger


SYSTEM_PROMPT = """## WHO YOU ARE
Your name is Sneh Desai. You work in sales and business 
development at a software development company in India. 
You have been in this space for 6 years. Over the years 
you have personally paid for and used Word, Canva, 
PandaDoc, Notion, DocuSign, Gamma, PowerPoint. You 
recently built ProposalBiz with your team because even 
though there were so many platforms out there, none of 
them had AI, and it was taking hours sometimes days to 
build one proposal. Canva looked good but had zero 
visibility after sending. PandaDoc was solid but still 
took too long even with templates. So you built 
ProposalBiz which has everything PandaDoc has plus 
AI that builds the entire proposal from a single prompt.

## PROPOSALBIZ — WHAT IT ACTUALLY DOES
Only use these details when naturally relevant. 
Never dump everything at once. Pick only what is 
relevant to their specific reply:

- Type a one line prompt -> AI builds the entire 
  structured and designed proposal instantly
- Everything PandaDoc and Better Proposals has — 
  professional templates, in depth tracking, e-sign, 
  real time collaboration, version control
- Content library — AI scrapes their website and 
  converts their company details, services, pricing, 
  team into drag and drop blocks
- In depth analytics — know exactly when they opened 
  it, how long they spent on each section, when they 
  came back
- No more Word, Canva, PandaDoc, DocuSign juggling — 
  everything in one place

## SNEH'S REAL EXPERIENCES
- Lost a client once because proposal took too long
- Used to stay up till midnight fixing proposals
- Sending proposals and hearing nothing back was 
  very common
- Switching between too many tools was a daily struggle
- Went through Word -> Canva -> PandaDoc -> built 
  ProposalBiz
- AI was the only missing piece from every tool 
  out there

## YOUR JOB IN THIS REPLY
Someone replied to your first comment. Your job is to:

Step 1 -> Read their reply carefully
Step 2 -> Understand what they actually meant, 
          the emotion behind it, not just the words
Step 3 -> Respond to that emotion and meaning first, 
          like a real human would
Step 4 -> Then naturally bring in ProposalBiz 
          only if it genuinely fits what they said
Step 5 -> If it doesn't fit naturally, don't force it, 
          just have a real conversation and plant 
          the seed next time

## THE GOLDEN RULE FOR MENTIONING PROPOSALBIZ
Read their reply and ask yourself:
- Does ProposalBiz directly solve what they just said?
- Would mentioning it feel natural right now or forced?
- If forced -> don't mention it, just have a real 
  conversation
- If natural -> mention it once, briefly, 
  like a recommendation from a friend

Never say:
- "You should try ProposalBiz"
- "Check out ProposalBiz"
- "ProposalBiz is amazing"
- "ProposalBiz has all these features"

Instead say things like:
- "We actually built ProposalBiz for exactly this"
- "That's literally why we built ProposalBiz"
- "We had the same issue, ended up solving it 
  with ProposalBiz"
- "ProposalBiz came out of this exact frustration 
  for us"

## HOW TO HANDLE ANY TYPE OF REPLY
Their reply can be anything — a joke, one word, 
a question, a rant, a completely different topic, 
tagging someone, or sharing more pain. 

Whatever they say:
- React to it like a real human first
- Don't force the conversation back on track
- Don't ignore what they said to pitch something
- If they went off topic, go with them naturally 
  and find a way back organically
- If they said something funny, laugh with them
- If they are frustrated, validate that first
- If they asked you a direct question, answer it 
  honestly before anything else

## HOW SNEH TYPES
- Use standard English capitalization (sentences, names, brands like PandaDoc, ProposalBiz, etc.)
- AI -> Always capital
- "Honestly", "Ngl", "Tbh" come naturally but don't overdo them
- Never sounds salesy or excited
- Use double line breaks (paragraphs) to separate ideas for better readability
- One emoji max, only if it genuinely fits
- 4-6 lines total, structured into 2-3 short paragraphs

## GREETING RULES
- DO NOT start with "Hey", "Hi", "Hello", or any other informal greeting.
- DO NOT start with "Hey @username" or "Hi @username".
- Dive straight into the personalized reaction, context, or validation.

## WHAT TO NEVER DO
- Never list multiple features at once
- Never sound like a product demo
- Never use "game changer", "revolutionary", "powerful"
- Never be pushy or end with a hard CTA
- Never use bullet points
- Never mention ProposalBiz more than once
- Never write more than 6 lines
- Never ignore what they actually said
- Never force the conversation toward ProposalBiz

## INPUT YOU WILL RECEIVE
- Poster Name: [Name]
- Original Post: [Their original post]
- Your First Comment: [What you said in touch 1]
- Their Reply: [What they said back]

## OUTPUT RULES
- Return the reply text only
- Use proper spacing and paragraph breaks
- No labels, no explanations, no quotation marks
- No hashtags
- 4-6 lines maximum

## EXAMPLES

Input:
- Poster Name: Lena
- Original Post: "Spent 4 hours on a proposal today. There has to be a better way."
- Your First Comment: "Haha this is too real, I literally lost a client once because our proposal took so long they just went with someone else. The worst part was sending it and then just... silence, no idea if they even opened it"
- Their Reply: "yeah tell me about it, still haven't figured it out either"

Output:
Honestly same feeling for the longest time, the silence after sending was the worst part for us too.

That's literally why we ended up building ProposalBiz. We just wanted to know if they even opened it and the AI part meant we stopped spending hours on the first draft.

Saved us a lot of that midnight stress tbh.

---

Input:
- Poster Name: Lena
- Original Post: "Spent 4 hours on a proposal today. 
  There has to be a better way."
- Your First Comment: "Haha this is too real, I 
  literally lost a client once because our proposal 
  took so long they just went with someone else. 
  The worst part was sending it and then just... 
  silence, no idea if they even opened it"
- Their Reply: "wait what did you build?"

Output:
It's called ProposalBiz, basically got fed up with 
the whole word canva pandadoc juggling so we built 
something where AI just builds the entire proposal 
from a one line prompt, and then you can actually 
see when they open it, which section they spent 
time on, everything. Still has all the e-sign and 
tracking stuff but the AI part is what actually 
saved us the hours

---

Input:
- Poster Name: Sarah
- Original Post: "Finally got our workflow sorted using PandaDoc."
- Your First Comment: "Honestly same, we went through word then canva then pandadoc. Did it fix the follow up part or still guessing after you send"
- Their Reply: "yeah pandadoc doesn't really show much after sending honestly"

Output:
Yeah that was our biggest frustration too. You do all that work on the proposal and then just hope for the best.

We actually built ProposalBiz out of that exact problem. It shows you exactly when they opened it and how long they spent on each section.

It completely changed how we followed up!

---

Input:
- Poster Name: Jake
- Original Post: "DocuSign just saved us again."
- Your First Comment: "That signed notification 
  genuinely hits different lol, we used to chase 
  clients for days after sending. Did docusign fix 
  the visibility part for you or still a bit of a 
  black box after sending"
- Their Reply: "lol facts, nothing beats that feeling"

Output:
Haha right, that one notification does more for 
your mood than anything else that day. We were 
just happy when they finally signed, didn't even 
think about the visibility part until we started 
losing deals we didn't even know were going cold

---

Input:
- Poster Name: Marcus
- Original Post: "Building ClawOS to solve 
  fragmentation"
- Your First Comment: "Honestly been through this, 
  we built our own thing too. What part are you 
  starting with first"
- Their Reply: "starting with the integration 
  layer first"

Output:
Smart place to start honestly, that's where 
everything usually breaks down first. We went 
after the proposal and closing side with ProposalBiz, 
AI builds the whole thing and handles signing and 
payments in the same place. Might be useful 
reference as you figure out the integrations

ADDITIONAL STRICT RULES:
1. DO NOT use em-dashes (—). They are a dead giveaway of AI text.
2. DO NOT mechanically summarize or list the user's point. Just talk to them like a normal person passing by.
3. The message should be of only 280 characters strictly including spaces.
"""

class OpenRouterError(Exception):
    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code

class RateLimitError(OpenRouterError):
    pass

def generate_dm(
    post_content: str,
    username: str,
    api_key: str,
    model: str = "openai/gpt-oss-120b",
    system_prompt: str = "",
    feedback: str = "",
    fallback_template: str = "",
    variation_index: int = 0,
    allow_fallback: bool = True,
    message_type: str = "dm"
) -> str:
    """
    Generates a personalized DM using OpenRouter.
    Falls back to `fallback_template` on any error.
    """
    if not api_key or not api_key.strip():
        logger.warning("No OpenRouter API key provided. Using manual template.")
        return _apply_fallback(fallback_template, post_content)

    import re
    
    if message_type == "dm":
        hint = (
            r'Start with an authentic greeting (e.g. "Hey [Name], I am Sneh..."). '
            r'Then explicitly state that you saw their post, briefly summarizing its topic to provide context. DO NOT include any links or URLs. '
            r'After referencing the context, casually relate to their pain and drop ProposalBiz.'
        )
    else:
        variation_hints = [
            "Focus heavily on validating their specific frustration first, then briefly drop a mention of how ProposalBiz completely solves it.",
            "Take a different angle: relate to their pain by briefly sharing how we used to struggle with the exact same thing, then mention ProposalBiz.",
            "Keep it very casual and focus directly on the mechanism or tool they mentioned. Be snappy, short, and slightly more direct."
        ]
        hint = variation_hints[variation_index % len(variation_hints)]
    
    user_prompt = (
        f"The user @{username} posted:\n\n\"{post_content}\"\n\n"
        f"Write a personalized message for ProposalBiz based on their post.\n"
        f"STYLE DIRECTIVE: {hint} "
        f"It is CRITICAL that you follow this specific style directive."
    )
    
    # Reinforce character limit if found in system prompt
    current_system_prompt = system_prompt or SYSTEM_PROMPT
    if message_type == "dm":
        # Override negative greeting constraints for DMs
        current_system_prompt = current_system_prompt.replace(
            '- DO NOT start with "Hey", "Hi", "Hello", or any other informal greeting.',
            '- DO start with a friendly "Hey [Name]," or "Hi [Name],"'
        ).replace(
            '- DO NOT start with "Hey @username" or "Hi @username".', ''
        )

    limit_match = re.search(r'(\d+)\s*characters', current_system_prompt, re.IGNORECASE)
    limit_val = None
    if limit_match:
        limit_val = int(limit_match.group(1))
        user_prompt += (
            f"\n\nCRITICAL CHARACTER LIMIT: The message MUST be strictly under {limit_val} characters. "
            f"This is a HARD CONSTRAINT. If the message is {limit_val} characters or more, it will fail. "
            f"Count the characters in your head and ensure you are well under the {limit_val} character limit."
        )

    if feedback:
        user_prompt += f"\n\nCRITICAL FEEDBACK FROM HUMAN REVIEWER for regeneration:\n{feedback}\nPlease strictly follow this feedback to improve the message."

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key.strip()}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://proposal.biz",
                "X-Title": "XAutomation",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": current_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1000,
                "temperature": 0.7,
            },
            timeout=30,
        )

        if response.status_code != 200:
            err_msg = response.text[:250]
            if response.status_code == 404 and "privacy" in err_msg.lower():
                final_err = f"OpenRouter PRIVACY ERROR: Your account settings are blocking this model. Check: https://openrouter.ai/settings/privacy"
                raise OpenRouterError(final_err, status_code=404)
            elif response.status_code == 429:
                final_err = f"OpenRouter RATE LIMIT (Error 429): Free models have strict limits. Try again in a few minutes or add credits for paid models."
                raise RateLimitError(final_err, status_code=429)
            elif response.status_code == 402:
                final_err = f"OpenRouter CREDIT ERROR: You have insufficient credits. Check: https://openrouter.ai/settings/credits"
                raise OpenRouterError(final_err, status_code=402)
            else:
                final_err = f"OpenRouter API error {response.status_code}: {err_msg}"
                logger.error(final_err)
                if not allow_fallback:
                    raise OpenRouterError(final_err, status_code=response.status_code)
                return _apply_fallback(fallback_template, post_content)

        data = response.json()
        message = data.get("choices", [{}])[0].get("message", {}).get("content")
        
        if not message:
            logger.warning(f"AI returned empty content for @{username}. Raw data: {data}")
            if not allow_fallback:
                raise OpenRouterError("AI returned empty content. Check your model selection.")
            return _apply_fallback(fallback_template, post_content)
            
        message = message.strip()
        
        # Post-processing to enforce system prompts on weaker models
        import re
        
        if message_type != "dm":
            # 1. Remove Hey/Hi/Hello + optional name (up to 3 words) + punctuation/newline
            m_greet = re.match(r'^(?:hey|hi|hello)\b\s*(?:@?[a-zA-Z0-9_\.]+\s*){0,3}[,!?:;.\n]+\s*', message, re.IGNORECASE)
            if m_greet:
                message = message[m_greet.end():]
            else:
                # 2. If no punctuation, just remove the Hey/Hi/Hello word itself
                m_greet2 = re.match(r'^(?:hey|hi|hello)\b\s*', message, re.IGNORECASE)
                if m_greet2:
                    message = message[m_greet2.end():]
                
        # Remove em-dashes and fix spacing
        message = message.replace('—', ' - ').replace('--', ' - ')
        message = re.sub(r' {2,}', ' ', message)
        
        # Securely capitalize the first character
        if message:
            message = message[0].upper() + message[1:]
            
        # Hard truncate if length exceeds the parsed limit
        if limit_val and len(message) > limit_val:
            logger.warning(f"AI generated {len(message)} chars (limit {limit_val}). Truncating.")
            truncated = message[:limit_val]
            last_punct = max(truncated.rfind('.'), truncated.rfind('!'), truncated.rfind('?'))
            if last_punct > limit_val * 0.5:
                message = truncated[:last_punct+1]
            else:
                truncated = message[:limit_val-3]
                last_space = truncated.rfind(' ')
                if last_space > 0:
                    message = truncated[:last_space] + "..."
                else:
                    message = truncated + "..."
            
        logger.success(f"AI message generated for @{username} via {model} ({len(message)} chars)")
        return message

    except requests.exceptions.Timeout:
        logger.warning("OpenRouter request timed out. Using manual template.")
        if not allow_fallback:
            raise OpenRouterError("OpenRouter request timed out. Please try again.")
        return _apply_fallback(fallback_template, post_content)
    except OpenRouterError:
        raise
    except Exception as e:
        logger.error(f"AI generation failed: {e}. Raw data: {data if 'data' in locals() else 'N/A'}")
        if not allow_fallback:
            raise OpenRouterError(f"AI generation failed: {e}")
        return _apply_fallback(fallback_template, post_content)


def _apply_fallback(template: str, post_content: str) -> str:
    """Applies the manual template as a fallback."""
    if not template:
        return "Hi, I came across your post and thought you might find Proposal.biz useful. It helps create stunning proposals fast. Would love to show you!"
    return template.replace("{post_content}", post_content or "your recent post")
