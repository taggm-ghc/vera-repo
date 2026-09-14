# VERA

## Verifiable Evidence-based Research Answers

**VERA is a provenance-grounded agentic context-engineering system that
discovers, critically evaluates, registers, and organizes evidence into
an auditable reasoning context to produce research responses measurably
superior to direct leading-LLM baselines.**

VERA is being developed as a capstone project for TAI Labs' Agentic AI
Engineering program.

## The Problem

Large language models can produce fluent research answers without making
the underlying evidence-selection process sufficiently inspectable.

A plausible answer is not necessarily a well-supported answer.
Conversely, an elaborate research process has limited value if its final
answer is no better than what a leading model can produce directly.

VERA therefore treats both **evidentiary defensibility** and **response
quality** as requirements.

The project examines a bounded question:

> Can deliberate, auditable evidence acquisition, critical evaluation,
> and context construction cause a frontier model to produce a
> materially better research response than it produces directly?

## What VERA Does

Given a bounded research question, VERA:

-   discovers and critically evaluates relevant evidence;
-   preserves evidence provenance;
-   constructs a deliberately selected research context;
-   produces a grounded research response; and
-   evaluates the resulting response against a direct leading-model
    baseline.

At a public architectural level:

``` text
Research Question
       |
       v
Evidence Discovery and Evaluation
       |
       v
Provenance-Grounded Context
       |
       v
Research Synthesis
       |
       v
Evaluation
       |
       v
Auditable Research Answer
```

The internal decision structures, representations, scoring methods,
orchestration mechanisms, and other implementation details used to
perform these functions are outside the scope of this public repository.

## Design Objectives

VERA is designed around four public objectives:

**Grounding.** Research claims should be supported by relevant evidence
rather than generated solely from model parameters.

**Provenance.** Consequential evidence should remain traceable to its
source.

**Auditability.** Evidence-selection and evaluation decisions should be
inspectable.

**Response quality.** Provenance and auditability are requirements, but
they do not compensate for an inferior final answer.

## Comparative Evaluation

VERA is evaluated against direct responses to the same bounded research
question from leading language models.

The central question is whether supplying a deliberately constructed,
critically evaluated evidence context produces a materially better
research response than direct model generation.

Evaluation considers the quality of the resulting answer as well as the
traceability of its supporting evidence.

## API

VERA is implemented as a Python service using FastAPI.

The application interface includes:

``` text
GET  /health
POST /ask
```

`GET /health` provides a basic service health check.

`POST /ask` is the primary research-question interface and serves as the
entry point to VERA.

## Running Locally

### Requirements

-   Python 3.11+
-   Python virtual environment
-   required Python dependencies
-   required API credentials stored locally in `.env`

Do not commit `.env` or API credentials to source control.

Start the development service with:

``` bash
./run.sh
```

The default local address is:

``` text
http://127.0.0.1:8001
```

Health check:

``` text
http://127.0.0.1:8001/health
```

FastAPI documentation:

``` text
http://127.0.0.1:8001/docs
```

A different port can be supplied when starting the service:

``` bash
./run.sh 8000
```

## Current Status

VERA is under active development.

The project is progressing from architecture and MVP definition into
implementation. The current service foundation supports incremental
development toward the capstone demonstration.

Target capstone demonstration: **October 2026**.

## Demo-Day Success Criterion

The project succeeds if VERA can demonstrate that it:

> produces a grounded research response significantly superior in
> quality to direct responses to the same research question from GPT-6
> Astra and other leading LLMs, while making its evidence-selection
> process inspectable and auditable.

Every consequential evidence decision should be traceable to its source,
evidence, provenance, and evaluation method.

A sophisticated and auditable process that produces an inferior research
answer does not satisfy the project's success criterion.

## Public Disclosure Boundary

This repository is publicly accessible for educational demonstration,
evaluation, and portfolio purposes.

It describes VERA's purpose, public capabilities, interfaces,
development status, and evaluation objectives. It intentionally does not
document proprietary internal representations, decision structures,
scoring methods, algorithms, orchestration, feedback mechanisms, private
architectures, or other non-public implementation details.

Public availability of this repository should not be interpreted as
disclosure of those non-public mechanisms.

## Project

**VERA: Verifiable Evidence-based Research Answers**

TAI Labs Agentic AI Engineering Capstone\
2026

Copyright © 2026 Tagg Maiwald. All rights reserved.
