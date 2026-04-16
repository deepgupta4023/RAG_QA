
Chosen file:Microsoft 2025 Annual Report

Reason:
-it is a public
-well-structured
-machine-readable 
-annual report from a major company
-mix of narrative sections
-business descriptions
-risks and financial information


Problems faced:
1. Tried chunking sentence wise but the overlap was off and chunks didn't make any sense . Solution: chunked using paragraphs
2. retrieval is working, but the ranking is poor: for an obvious question like “What were Microsoft’s three core business priorities?”, the top result is an unrelated financial-notes chunk instead of the actual OUR PRIORITIES section. That suggests the issue is not parsing or chunking now, but similarity ranking. Solution: rebuild the Chroma collection using cosine distance instead of the default setup
3. The vector search is returning semantically similar but wrong chunks for an obvious question.
The actual answer exists in the document, but dense retrieval alone is not ranking it high enough.