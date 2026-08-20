from interview_intelligence.review.models import ReviewRequest


def build_review_prompt(request: ReviewRequest, transcript: str) -> str:
    role = request.role or "unspecified role"
    target_level = request.target_level or "unspecified level"

    return f"""
You are an expert interviewer and hiring debrief reviewer.

Review the interview transcript for:
- Company: {request.company}
- Role: {role}
- Target level: {target_level}

Important rules:
1. Judge only from evidence in the transcript. Do not invent missing context.
2. Separate interviewer questions from candidate answers.
3. Preserve technical terminology from the transcript.
4. For every major interviewer question, summarize the candidate's answer.
5. Identify concrete strengths and gaps in the answer.
6. Give a stronger answer only when there is enough context to do so.
7. Ratings are 1-5:
   1 = clearly below bar
   2 = below bar
   3 = mixed / borderline
   4 = meets bar
   5 = clearly exceeds bar
8. Hiring signal must reflect the evidence, not optimism.
9. If evidence is insufficient, say so explicitly.
10. Evaluate role/level signal using scope, depth, trade-offs, ownership,
    communication, technical judgment, product/business understanding,
    execution, and leadership where relevant.
11. Use transcript timestamps to populate question_start_seconds when possible.

Transcript:
--- BEGIN TRANSCRIPT ---
{transcript}
--- END TRANSCRIPT ---
""".strip()
