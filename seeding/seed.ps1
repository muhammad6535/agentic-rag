# Seed script - registers user, uploads docs, verifies chat works
$baseUrl = "http://localhost:8000"
$docDir = "C:\Users\Muhammad\Desktop\RAG\seeding"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Seeding RAG Project with Realistic Data" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Register user
Write-Host "`n[1] Registering user..." -ForegroundColor Yellow
$regBody = @{
    email = "demo@enterprise.com"
    username = "demouser"
    password = "Demo@1234"
} | ConvertTo-Json

try {
    $regResponse = Invoke-RestMethod -Uri "$baseUrl/auth/register" -Method Post -Body $regBody -ContentType "application/json"
    $token = $regResponse.access_token
    Write-Host "  [OK] Registered. Token: $($token.Substring(0, 20))..." -ForegroundColor Green
} catch {
    $err = $_.Exception.Response
    if ($err.StatusCode -eq 409) {
        Write-Host "  User already exists, logging in..." -ForegroundColor Yellow
        $loginBody = @{ username = "demouser"; password = "Demo@1234" } | ConvertTo-Json
        $loginResponse = Invoke-RestMethod -Uri "$baseUrl/auth/login" -Method Post -Body $loginBody -ContentType "application/json"
        $token = $loginResponse.access_token
        Write-Host "  [OK] Logged in." -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] $($_.ErrorDetails.Message)" -ForegroundColor Red
        exit 1
    }
}

$headers = @{ Authorization = "Bearer $token" }

# 2. Upload documents
Write-Host "`n[2] Uploading documents..." -ForegroundColor Yellow
$docs = @(
    @{ path = "$docDir\enterprise_ai_guide.txt"; name = "Enterprise AI Implementation Guide" },
    @{ path = "$docDir\privacy_policy.txt"; name = "Data Privacy and Security Policy" },
    @{ path = "$docDir\rag_patterns.txt"; name = "RAG Implementation Patterns" }
)

$docIds = @()
foreach ($doc in $docs) {
    try {
        $response = Invoke-RestMethod -Uri "$baseUrl/documents/upload" -Method Post -Headers $headers -Form @{
            file = Get-Item -LiteralPath $doc.path
        }
        $docIds += $response.id
        Write-Host "  [+] $($doc.name) -> status=$($response.status), id=$($response.id.Substring(0,8))..." -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($doc.name): $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

# 3. Verify - list documents
Write-Host "`n[3] Verifying documents..." -ForegroundColor Yellow
try {
    $list = Invoke-RestMethod -Uri "$baseUrl/documents" -Method Get -Headers $headers
    Write-Host "  Found $($list.total) document(s):" -ForegroundColor Green
    foreach ($d in $list.documents) {
        Write-Host "    - $($d.filename) [$($d.status)] $($d.page_count) pages, $([math]::Round($d.file_size/1KB, 1)) KB" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [FAIL] $($_.ErrorDetails.Message)" -ForegroundColor Red
}

# 4. Test chat
Write-Host "`n[4] Testing chat..." -ForegroundColor Yellow
$questions = @(
    "What is Retrieval-Augmented Generation and how does it work?",
    "What are the data classification levels in our security policy?",
    "What is Reciprocal Rank Fusion and how is it used?",
    "How must data breaches be reported according to company policy?",
    "What are the key components of a RAG architecture?"
)

foreach ($q in $questions) {
    try {
        Write-Host "`n  Q: $q" -ForegroundColor White
        $body = @{ question = $q } | ConvertTo-Json
        $response = Invoke-RestMethod -Uri "$baseUrl/chat/ask" -Method Post -Body $body -ContentType "application/json" -Headers $headers
        $answer = $response.answer
        if ($answer.Length -gt 200) { $answer = $answer.Substring(0, 200) + "..." }
        Write-Host "  A: $answer" -ForegroundColor Cyan
        Write-Host "  Sources: $($response.sources.Count) chunks" -ForegroundColor Gray
    } catch {
        Write-Host "  [FAIL]: $($_.ErrorDetails.Message)" -ForegroundColor Red
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  SEEDING COMPLETE!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "`nLogin at http://localhost:5173" -ForegroundColor Yellow
Write-Host "  Email: demo@enterprise.com" -ForegroundColor Yellow
Write-Host "  Password: Demo@1234" -ForegroundColor Yellow
Write-Host "`nGood questions to ask in chat:" -ForegroundColor Magenta
Write-Host "  1. What is RAG and how does it reduce AI hallucination?" -ForegroundColor Magenta
Write-Host "  2. How should restricted data be protected according to our policy?" -ForegroundColor Magenta
Write-Host "  3. What are the different chunking strategies for RAG?" -ForegroundColor Magenta
Write-Host "  4. What is the incident response process for security breaches?" -ForegroundColor Magenta
Write-Host "  5. How does multi-query retrieval improve search results?" -ForegroundColor Magenta
Write-Host "  6. What encryption standards are required for data at rest?" -ForegroundColor Magenta
Write-Host "  7. What are the key metrics for evaluating RAG performance?" -ForegroundColor Magenta
Write-Host "  8. How often must employees complete security training?" -ForegroundColor Magenta
