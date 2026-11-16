import requests
import json

resume_id = "e3357f64-3994-4ef3-87b5-b25273568f10"
job_id = "960bdb94-c807-407f-b86d-002c1b82215a"

url = "http://127.0.0.1:8000/api/v1/matching/evaluate"
payload = {
    "job_id": job_id,
    "resume_ids": [resume_id],
    "use_semantic": True
}

response = requests.post(url, json=payload)

print(f"Response status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"PASS: Matching successful")
    print(f"\nJob ID: {data['job_id']}")
    print(f"Total candidates: {data['total_candidates']}")
    print(f"Successful: {data['successful']}")
    print(f"Failed: {data['failed']}")
    
    if data['results']:
        result = data['results'][0]
        print(f"\nResume ID: {result['resume_id']}")
        print(f"Filename: {result['filename']}")
        print(f"Candidate Name: {result['candidate_name']}")
        
        match = result['match_result']
        print(f"\n=== Scoring Components ===")
        print(f"Overall Score: {match['overall_score']}")
        print(f"TF-IDF Score: {match['tfidf_score']}")
        print(f"Semantic Score: {match['semantic_score']}")
        print(f"Skill Match Score: {match['skill_match_score']}")
        
        print(f"\n=== Required Skills ===")
        print(f"Matched ({len(match['matched_skills'])}): {match['matched_skills']}")
        print(f"Missing ({len(match['missing_skills'])}): {match['missing_skills']}")
        
        print(f"\n=== Preferred Skills ===")
        print(f"Additional ({len(match['additional_skills'])}): {match['additional_skills']}")
        
        print(f"\n=== Coverage ===")
        print(f"Required Skill Coverage: {match['required_skill_coverage']}")
        print(f"Preferred Skill Coverage: {match['preferred_skill_coverage']}")
        
        print(f"\n=== Evidence ===")
        if match['skill_evidence']:
            for skill, evidence_list in match['skill_evidence'].items():
                print(f"\nSkill: {skill}")
                for ev in evidence_list[:2]:  # Show first 2 evidence items
                    print(f"  - Section: {ev['section']}")
                    print(f"    Type: {ev['evidence_type']}")
                    print(f"    Strength: {ev['strength']}")
                    print(f"    Snippet: {ev['snippet'][:100]}...")
        else:
            print("No evidence generated")
        
        print(f"\n=== Scoring Strategy ===")
        if match['scoring_strategy']:
            print(f"Algorithm Version: {match['scoring_strategy']['algorithm_version']}")
            print(f"Components: {match['scoring_strategy']['components']}")
            print(f"Weights: {match['scoring_strategy']['weights']}")
            print(f"Semantic Available: {match['scoring_strategy']['semantic_available']}")
            print(f"Fallback Used: {match['scoring_strategy']['fallback_used']}")
        
        print(f"\n=== Explanation ===")
        print(match['explanation'])
        
        # Check for zero required skills issue
        if len(match['matched_skills']) == 0 and len(match['missing_skills']) > 0:
            print(f"\nWARNING: Zero matched skills despite missing skills - investigate")
        else:
            print(f"\nPASS: Matched skills count is reasonable")
            
else:
    print(f"FAIL: HTTP {response.status_code}")
    print(f"Response: {response.text}")
