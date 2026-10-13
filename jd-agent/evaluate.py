import json

from api import calculate_match_score


with open("test_cases.json", "r", encoding="utf-8") as file:
    test_cases = json.load(file)

passed = 0

for case in test_cases:
    result = calculate_match_score(
        required_skills=case["required_skills"],
        candidate_skills=case["candidate_skills"],
    )

    actual_score = result["score"]
    expected_score = case["expected_score"]
    is_passed = actual_score == expected_score

    if is_passed:
        passed += 1

    status = "通过" if is_passed else "失败"
    print(
        f'{case["name"]}: {status} '
        f"(实际={actual_score}, 预期={expected_score})"
    )

total = len(test_cases)
rate = passed / total * 100

print(f"\n通过率：{passed}/{total} = {rate:.0f}%")