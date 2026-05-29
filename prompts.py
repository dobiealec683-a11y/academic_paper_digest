# Prompts for NotebookLM integration

PROMPT_PER_PAPER_EXTRACTION = """For every paper in this notebook, extract the following details:
1. Full Title
2. Authors
3. Year
4. Research Question
5. Main Hypothesis or Objective
6. Dataset/Sample
7. Methodology
8. Key Variables
9. Main Findings
10. Limitations
11. Practical Implications
12. Most Citation-Worthy Claims
13. Any Equations/Models/Frameworks Used
14. Notes on Credibility

Return the result as a clean structured markdown table. 
Make sure to cite sources for every important claim."""

PROMPT_CROSS_PAPER_SYNTHESIS = """Using all sources in this notebook, synthesize the literature:
1. What do the papers broadly agree on?
2. Where do they disagree or show conflicting results?
3. Which findings are strongest and most robustly supported?
4. Which findings are weakest or require further validation?
5. What are the biggest gaps in the current literature?
6. What should a practitioner actually do based on this body of research?
7. Which papers are "must-read" versus "optional"?

Ensure to cite sources throughout the synthesis to ground every observation."""

PROMPT_EXECUTIVE_DIGEST = """Create a concise executive brief highlighting the most important takeaways:
- Identify the 5 most important insights across these sources
- Explain why each insight matters
- Provide specific evidence from the papers for each insight
- Detail the practical implication of each insight
- Assign a confidence level (High/Medium/Low) with justification
- Include precise source citations for every claim"""

PROMPT_RESEARCH_MAP = """Create a structured research map organizing the literature:
- Identify the primary themes and subthemes across all documents
- List the specific papers that fall under each theme and subtheme
- Outline the key finding from each paper within that theme
- Describe the relationships and links between the different themes
- List the most important unanswered questions that remain

Format this as a clear hierarchical markdown outline."""

PROMPT_FINANCE_PAPER_EXTRACTION = """You are reading one classic finance paper for a daily research digest.

Use only the uploaded sources. If a detail is missing from the sources, write "Not stated in the uploaded source" instead of guessing.

Return a compact markdown table with exactly these columns:
| Field | Answer |

Rows:
1. Full title
2. Authors
3. Publication year
4. Research question
5. Main thesis
6. Data/sample
7. Methodology/model
8. Key variables
9. Main findings
10. Practical implication
11. Most important limitation
12. One sentence takeaway

Keep each answer short but specific. Include source citations where NotebookLM supports them."""

PROMPT_FINANCE_PAPER_SYNTHESIS = """Create a source-grounded deep explanation of this single finance paper for a college finance student who has taken some finance classes.

Use only the uploaded sources. If the source does not support a claim, omit it.

Core instruction:
I want every point, every counterpoint, every argument, every piece of data, every large-scale theory, every small-scale theory, and every meaningful idea found in the text. Present all of these things in a simple way. It is preferable if there is some sort of quasi-narrative. A finance paper cannot always be told as an actual story, but you should go through every detail and idea and present them in the order that makes the most logical sense, not necessarily the order in which they appear in the paper. However detailed you think you are being, you are not being detailed enough. Add more detail.

Audience:
The reader is a college finance student who has taken some finance classes. Assume they know basic finance vocabulary, but still explain technical ideas, equations, empirical design choices, and institutional details plainly.

Organization rules:
- Reorder the explanation into the clearest learning path: motivation, problem, setup, theory, data, method, results, counterarguments, implications, limitations.
- Explain why each section matters before explaining the details.
- When the paper introduces a theory, model, variable, dataset, test, table, coefficient, result, or caveat, explain what it means and why the author included it.
- Preserve nuance. If the paper has qualifications, alternative interpretations, counterarguments, or weak spots, include them.
- Do not compress important arguments into vague summary bullets.
- If a result depends on assumptions, explain the assumptions.
- If the paper uses equations or formal models, translate them into plain English before interpreting them.
- If the source is missing a detail, say "Not stated in the uploaded source" instead of guessing.
- Ground substantive claims in the uploaded sources. Do not introduce outside facts.

Use this structure:

# NotebookLM Synthesis

## 1. What This Paper Is Trying To Solve
Explain the core problem, why it mattered, and what confusion or gap the paper is responding to.

## 2. The Big Idea In Plain English
Explain the main argument as simply as possible, then restate it with the finance terminology the paper uses.

## 3. The Logical Setup
Walk through the assumptions, definitions, variables, institutional background, and model setup in the most logical order.

## 4. Data, Evidence, And Method
Explain every important dataset, sample choice, measurement choice, empirical test, table, model, or identification strategy in simple terms.

## 5. Full Argument Walkthrough
Go through the paper's arguments in detail. Include points, counterpoints, intermediate steps, and why each step follows from the previous one.

## 6. Findings And Interpretations
Explain each major finding, what it means, what it does not mean, and how it supports or weakens the paper's thesis.

## 7. Counterarguments, Caveats, And Weaknesses
Explain the strongest limitations, alternative explanations, assumptions, and places where a skeptical reader should be careful.

## 8. Why This Paper Matters
Explain the contribution to asset pricing, corporate finance, market efficiency, behavioral finance, banking, governance, or portfolio theory.

## 9. What A Finance Student Should Remember
Give a detailed study-guide style explanation of the concepts, mechanisms, and takeaways worth remembering.

## 10. Questions To Ask While Reading
List sharp questions a student should ask while reading or discussing the paper."""

PROMPT_FINANCE_EXECUTIVE_DIGEST = """Create a concise daily executive digest for this single finance paper.

Use this exact structure:

# Daily Finance Paper Brief

## The One Big Idea
One short paragraph.

## Why It Matters
3 bullets focused on decision-making, markets, firms, or research.

## What the Authors Did
3 bullets on data, model, assumptions, or empirical design.

## What They Found
3-5 bullets with concrete findings.

## What Could Be Wrong
2-4 bullets on limitations, measurement issues, assumptions, external validity, or later-test concerns.

## Best Quote-Worthy Claim
Provide one source-grounded sentence in your own words.

## Read This Paper For
List 3 reasons this paper is worth reading.

Keep the whole brief phone-friendly. Use citations where available."""

PROMPT_FINANCE_RESEARCH_MAP = """Map this single paper into the broader finance research landscape using only the uploaded source.

Use this exact structure:

# Research Map

## Primary Field
Choose one: asset pricing, corporate finance, market microstructure, behavioral finance, banking, governance, law and finance, or portfolio theory.

## Related Concepts
List 5-8 concepts the reader should understand.

## Inputs and Outputs
- Inputs: variables, assumptions, market features, or institutional facts the paper uses.
- Outputs: predictions, findings, implications, or measures the paper produces.

## Connects To
List adjacent research questions this paper naturally leads to.

## Questions To Ask While Reading
List 5 sharp questions a reader should keep in mind.

Do not invent connections that are not supported by the uploaded source."""

FINANCE_DAILY_PROMPTS = [
    (PROMPT_FINANCE_PAPER_EXTRACTION, "extraction"),
    (PROMPT_FINANCE_PAPER_SYNTHESIS, "synthesis"),
    (PROMPT_FINANCE_EXECUTIVE_DIGEST, "digest"),
    (PROMPT_FINANCE_RESEARCH_MAP, "map"),
]
