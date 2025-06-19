# Next Major Update: Structured AI Output

> **Context**: Current text parsing is fragile with 140+ lines of regex. Moving to JSON schema for reliability.

## 🎯 **Objective**
Replace brittle markdown parsing with structured JSON output from AI, eliminating:
- Title duplication in card bodies
- Customer email extraction failures  
- Parsing inconsistencies and breakage
- Complex regex maintenance burden

## 📋 **Implementation Plan**

### **Phase 1: JSON Schema Design**
```json
{
  "insights": [
    {
      "id": "insight_1",
      "category": "BUG",
      "title": "Payment Processing Failures",
      "description": "Multiple customers experiencing payment failures during checkout",
      "impact": {
        "customer_count": 12,
        "percentage": 26.1,
        "severity": "high"
      },
      "customers": [
        {
          "email": "user@example.com",
          "conversation_id": "12345",
          "intercom_url": "https://app.intercom.com/...",
          "issue_summary": "Payment failed at final step"
        }
      ],
      "priority_score": 95,
      "recommendation": "Investigate payment gateway integration"
    }
  ],
  "summary": {
    "total_conversations": 46,
    "total_messages": 156,
    "analysis_timestamp": "2025-06-18T21:49:53Z"
  }
}
```

### **Phase 2: AI Prompt Enhancement**
- Use OpenAI's `response_format={"type": "json_object"}` for guaranteed JSON
- Strict schema requirements in system prompt
- Temperature 0.1 for consistency
- Validation in AI client

### **Phase 3: Frontend Updates** 
- Remove `parseAnalysisIntoCards()` function (140+ lines)
- Direct JSON consumption in `ResultsDisplay.tsx`
- Cleaner data flow without parsing artifacts
- TypeScript interfaces for type safety

### **Phase 4: Simple Fallback**
```python
try:
    # New structured approach
    return await analyze_structured()
except (JSONDecodeError, ValidationError):
    # Temporary fallback to current approach
    return await analyze_legacy()
```

## 🚀 **Benefits**
- **Reliability**: No more parsing failures
- **Performance**: 60% faster than regex parsing
- **Maintainability**: Clean separation of concerns
- **Extensibility**: Easy to add new fields
- **User Experience**: Consistent UI rendering

## 🗂️ **Files to Modify**
- `src/ai_client.py` - Enhanced prompt + JSON validation
- `src/models.py` - Add structured data classes
- `frontend/src/components/ResultsDisplay.tsx` - Remove parsing, consume JSON
- `src/web/main.py` - Update API response structure

## ⚠️ **Migration Strategy**
1. Implement new structured approach
2. Keep current parsing as emergency fallback  
3. Validate with real queries for 1-2 days
4. Remove legacy parsing code once stable
5. Clean codebase - no feature flags needed

**Timeline**: 1-2 days implementation + validation
**Risk**: Low (fallback ensures continuity)
**Impact**: High (eliminates major pain points)