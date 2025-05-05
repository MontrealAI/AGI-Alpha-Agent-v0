SAMPLE_TASKS = [
    {
        "prompt": "What is 2 + 2?",
        "judge": lambda out: 1.0 if "4" in out else 0.0
    },
]
