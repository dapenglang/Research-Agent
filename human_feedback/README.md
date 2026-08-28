# Human-in-the-loop Feedback

## Usage

This directory stores human feedback files. When a module pauses for human review,
the pipeline will check for the corresponding feedback file in this directory.

## Feedback Files

### innovation_feedback.md
- **Trigger**: Module 05 (Innovation Reasoning) completes
- **Purpose**: Allow human to modify/add innovation directions
- **Action**: Pipeline reads this file after Module 05 and incorporates feedback into Module 06

### method_feedback.md
- **Trigger**: Module 06 (Theory & Method) completes
- **Purpose**: Allow human to adjust method design, algorithms, formulas
- **Action**: Pipeline reads this file after Module 06 and incorporates feedback into Module 07

### review_response.md
- **Trigger**: Module 14 (Reviewer) completes
- **Purpose**: Allow human to respond to reviewer comments and guide revisions
- **Action**: Pipeline reads this file after Module 14 and incorporates responses into revision

## Format

Each feedback file should be in Markdown format. The pipeline will read the entire
file content and pass it to the downstream module as additional context.

## Workflow

1. Pipeline runs Module 05 and generates innovation_report.md
2. Pipeline checks if human_in_loop is enabled for Module 05
3. If enabled, pipeline pauses and prints: "Waiting for human feedback in human_feedback/innovation_feedback.md"
4. Human fills in innovation_feedback.md with corrections/additions
5. Human resumes pipeline (via CLI `resume` command)
6. Pipeline reads feedback and passes it to Module 06

## Notes

- If the feedback file is empty or does not exist, the pipeline continues normally
- Feedback files are preserved across pipeline runs for reference
- Multiple rounds of feedback are supported via the resume/rerun mechanism
