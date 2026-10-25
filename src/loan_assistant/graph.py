import os

from langchain_aws import ChatBedrockConverse
from langgraph.graph import StateGraph, START, END

from .state import (LoanState)    

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "us.amazon.nova-micro-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
llm = ChatBedrockConverse(model_id=MODEL_ID, temperature=0, region_name=AWS_REGION)


def document_agent(state: LoanState) -> dict:
    return {
        "extracted_data": {"monthly_income": 4000, "monthly_outgoings": 2500}, 
        "audit_log": ["document agent ran"]
     }

def affordability_agent(state: LoanState) -> dict:
    data = state["extracted_data"]
    disposable = data["monthly_income"] - data["monthly_outgoings"]
    return {
        "affordability": {"disposable_income": disposable},
        "audit_log": ["affordability agent ran"],
    }

def policy_agent(state: LoanState) -> dict:
    disposable = state["affordability"]["disposable_income"]
    monthly_repayment = state["loan_amount"] / 36
    passed = monthly_repayment < disposable / 2

    if passed:
        reasons = ["repayment is under half of disposable income"]    
    else:    
        reasons = ["repayment is too high compared to disposable income"]

    return {
        "policy_check": {
            "passed": passed, 
            "reasons": reasons,
            "monthly_repayment": round(monthly_repayment, 2),
        },
        "audit_log": ["policy agent ran"],
    }

def route_after_policy(state: LoanState) -> str:
    if state["policy_check"]["passed"]:
        return "supervisor_agent"
    else:
        return "rejection"
    
def supervisor_agent(state: LoanState) -> dict:
    prompt = f"""
You are a loan underwriting assistant at a UK bank.
Write a 2-3 sentence recommendation for a human loan officer.
You recommend only; a human makes the final decision.
Loan amount: £{state["loan_amount"]}
Affordability: {state["affordability"]}
Policy check: {state["policy_check"]}"""
    
    response = llm.invoke(prompt)

    return {
        "recommendation": response.content,
        "audit_log": [f"supervisor agent ran (LLM: {MODEL_ID})"],
    }

def rejection(state: LoanState) -> dict:
    reasons = state["policy_check"]["reasons"]
    return {
        "recommendation": "Decline: " + "; ".join(reasons),
        "audit_log": ["rejection ran"],
    }

builder = StateGraph(LoanState)
builder.add_node("document_agent", document_agent)
builder.add_node("affordability_agent", affordability_agent)
builder.add_node("policy_agent", policy_agent)
builder.add_node("supervisor_agent", supervisor_agent)
builder.add_node("rejection", rejection)
builder.add_edge(START, "document_agent")
builder.add_edge("document_agent", "affordability_agent")
builder.add_edge("affordability_agent", "policy_agent")
builder.add_conditional_edges("policy_agent", route_after_policy)
builder.add_edge("rejection", END)
builder.add_edge("supervisor_agent", END)
graph = builder.compile()


if __name__ == "__main__":
    result = graph.invoke({"application_id": "A1", "loan_amount": 10000})
    print(result)