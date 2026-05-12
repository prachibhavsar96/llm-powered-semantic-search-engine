import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const API_BASE_URL = "http://127.0.0.1:8000";
const TOKEN_STORAGE_KEY = "llm_search_access_token";
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;
const INACTIVITY_TIMEOUT_MS = 60 * 60 * 1000;
const ACTIVITY_EVENTS = ["click", "keydown", "input", "mousemove", "scroll", "touchstart"];

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_STORAGE_KEY) || "");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [documents, setDocuments] = useState([]);
  const [recentSearches, setRecentSearches] = useState([]);
  const [dashboardStats, setDashboardStats] = useState({
    total_uploaded_files: 0,
    total_indexed_chunks: 0,
    total_searches: 0,
    average_search_time_ms: 0,
  });
  const [results, setResults] = useState([]);
  const [answerSummary, setAnswerSummary] = useState("");
  const [searchMeta, setSearchMeta] = useState(null);
  const [activeTab, setActiveTab] = useState("search");
  const [mode, setMode] = useState("search");
  const [chatMessages, setChatMessages] = useState([]);
  const [expandedChunkGroups, setExpandedChunkGroups] = useState({});
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(3);
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const inactivityTimerRef = useRef(null);

  useEffect(() => {
    if (token || !GOOGLE_CLIENT_ID) {
      return;
    }

    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      if (!window.google) {
        return;
      }

      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleLogin,
      });
      window.google.accounts.id.renderButton(
        document.getElementById("googleSignInButton"),
        { theme: "outline", size: "large", width: 280 }
      );
    };

    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, [token]);

  async function fetchDocuments() {
    if (!token) {
      setDocuments([]);
      return;
    }

    setError("");

    try {
      const response = await fetch(`${API_BASE_URL}/documents`, {
        headers: authHeaders(token),
      });

      if (!response.ok) {
        throw new Error("Could not load documents.");
      }

      const data = await response.json();
      setDocuments(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function fetchSearchHistory() {
    if (!token) {
      setRecentSearches([]);
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/search/history`, {
        headers: authHeaders(token),
      });

      if (!response.ok) {
        throw new Error("Could not load recent searches.");
      }

      const data = await response.json();
      setRecentSearches(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function fetchDashboardStats() {
    if (!token) {
      setDashboardStats({
        total_uploaded_files: 0,
        total_indexed_chunks: 0,
        total_searches: 0,
        average_search_time_ms: 0,
      });
      return;
    }

    setAnalyticsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/dashboard/stats`, {
        headers: authHeaders(token),
      });

      if (!response.ok) {
        throw new Error("Could not load dashboard stats.");
      }

      const data = await response.json();
      setDashboardStats(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyticsLoading(false);
    }
  }

  useEffect(() => {
    fetchDocuments();
    fetchSearchHistory();
    fetchDashboardStats();
  }, [token]);

  useEffect(() => {
    if (!token) {
      return;
    }

    function clearInactivityTimer() {
      if (inactivityTimerRef.current) {
        clearTimeout(inactivityTimerRef.current);
      }
    }

    function expireSession() {
      clearInactivityTimer();
      setToken("");
      setDocuments([]);
      setRecentSearches([]);
      setDashboardStats(emptyDashboardStats());
      setResults([]);
      setAnswerSummary("");
      setSearchMeta(null);
      setChatMessages([]);
      setSelectedFile(null);
      setError("");
      setMessage("Session expired due to inactivity.");
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    }

    function resetInactivityTimer() {
      clearInactivityTimer();
      inactivityTimerRef.current = setTimeout(expireSession, INACTIVITY_TIMEOUT_MS);
    }

    resetInactivityTimer();
    ACTIVITY_EVENTS.forEach((eventName) => {
      window.addEventListener(eventName, resetInactivityTimer);
    });

    return () => {
      clearInactivityTimer();
      ACTIVITY_EVENTS.forEach((eventName) => {
        window.removeEventListener(eventName, resetInactivityTimer);
      });
    };
  }, [token]);

  const indexedChunkGroups = groupIndexedChunks(documents);

  async function handleAuth(endpoint) {
    const trimmedEmail = email.trim();

    if (!trimmedEmail || !password.trim()) {
      setError("Enter both your email and password.");
      return;
    }

    if (!isValidEmail(trimmedEmail)) {
      setError("Enter a valid email address.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/auth/${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email: trimmedEmail, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Authentication failed.");
      }

      if (endpoint === "signup") {
        setMessage("Account created. You can log in now.");
        return;
      }

      setToken(data.access_token);
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      setMessage("Welcome back. You are logged in.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin(response) {
    setLoading(true);
    setError("");
    setMessage("");

    try {
      const authResponse = await fetch(`${API_BASE_URL}/auth/google`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ credential: response.credential }),
      });

      const data = await authResponse.json();

      if (!authResponse.ok) {
        throw new Error(data.detail || "Google login failed.");
      }

      setToken(data.access_token);
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      setMessage("Logged in with Google.");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    if (inactivityTimerRef.current) {
      clearTimeout(inactivityTimerRef.current);
    }

    setToken("");
    setDocuments([]);
    setRecentSearches([]);
    setDashboardStats(emptyDashboardStats());
    setResults([]);
    setAnswerSummary("");
    setSearchMeta(null);
    setActiveTab("search");
    setChatMessages([]);
    setError("");
    setMessage("");
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!selectedFile) {
      setError("Choose a .txt, .pdf, or .docx file before uploading.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${API_BASE_URL}/documents/upload`, {
        method: "POST",
        headers: authHeaders(token),
        body: formData,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Upload failed.");
      }

      const uploadedChunks = await response.json();
      setMessage(`Uploaded ${uploadedChunks.length} chunk(s) from ${selectedFile.name}.`);
      setSelectedFile(null);
      event.target.reset();
      await fetchDocuments();
      await fetchDashboardStats();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function runSearch(searchQuery) {
    const trimmedQuery = searchQuery.trim();

    if (!trimmedQuery) {
      setError("Enter a search query.");
      return;
    }

    setLoading(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/search`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(token),
        },
        body: JSON.stringify({
          query: trimmedQuery,
          top_k: Number(topK),
        }),
      });

      if (!response.ok) {
        throw new Error("Search failed.");
      }

      const data = await response.json();
      setResults(data.results);
      setAnswerSummary(data.answer_summary);
      setSearchMeta({
        executionTimeMs: data.execution_time_ms,
        totalDocumentsScanned: data.total_documents_scanned,
        cacheHit: data.cache_hit,
      });
      setMessage(
        `Found ${data.results.length} result(s) in ${data.execution_time_ms} ms. ` +
          `Scanned ${data.total_documents_scanned} document(s). Cache hit: ${data.cache_hit ? "yes" : "no"}.`
      );
      await fetchSearchHistory();
      await fetchDashboardStats();

      if (mode === "chat") {
        setChatMessages((current) => [
          ...current,
          {
            id: `${Date.now()}-user`,
            role: "user",
            content: trimmedQuery,
          },
          {
            id: `${Date.now()}-assistant`,
            role: "assistant",
            content: data.answer_summary,
            supportingChunks: data.results,
            meta: {
              executionTimeMs: data.execution_time_ms,
              cacheHit: data.cache_hit,
            },
          },
        ]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(event) {
    event.preventDefault();
    await runSearch(query);
  }

  async function handleRecentSearchClick(searchQuery) {
    setQuery(searchQuery);
    await runSearch(searchQuery);
  }

  if (!token) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <p className="eyebrow">Semantic document search</p>
          <h1>LLM-Powered Q&A Search Engine</h1>
          <p className="subtitle">
            Sign up or log in to upload private documents and search only your own indexed chunks.
          </p>

          {(error || message) && (
            <div className="status-area toast-area">
              {error && <p className="status error">{error}</p>}
              {message && <p className="status success">{message}</p>}
            </div>
          )}

          <div className="auth-form">
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="email@example.com"
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="At least 6 characters"
              />
            </label>
            <div className="auth-actions">
              <button type="button" onClick={() => handleAuth("login")} disabled={loading}>
                {loading ? "Checking..." : "Log in"}
              </button>
              <button
                type="button"
                className="secondary-button"
                onClick={() => handleAuth("signup")}
                disabled={loading}
              >
                {loading ? "Working..." : "Sign up"}
              </button>
            </div>
          </div>

          <div className="auth-divider">or</div>

          {GOOGLE_CLIENT_ID ? (
            <div id="googleSignInButton" className="google-button-slot" />
          ) : (
            <button type="button" className="google-fallback" disabled>
              Continue with Google
            </button>
          )}
          {!GOOGLE_CLIENT_ID && (
            <p className="helper-text">
              Add `VITE_GOOGLE_CLIENT_ID` to enable Google sign-in.
            </p>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <section className="page-header">
        <div>
          <p className="eyebrow">Semantic document search</p>
          <h1>LLM-Powered Q&A Search Engine</h1>
          <p className="subtitle">
            Upload a text, PDF, or Word file, ask a question, and review a rule-based answer with ranked source chunks.
          </p>
        </div>
        <button type="button" className="secondary-button" onClick={handleLogout}>
          Log out
        </button>
      </section>

      {(error || message) && (
        <section className="status-area toast-area">
          {error && <p className="status error">{error}</p>}
          {message && <p className="status success">{message}</p>}
        </section>
      )}

      <nav className="dashboard-tabs" aria-label="Dashboard sections">
        <button
          type="button"
          className={activeTab === "search" ? "active" : ""}
          onClick={() => setActiveTab("search")}
        >
          Ask AI
        </button>
        <button
          type="button"
          className={activeTab === "documents" ? "active" : ""}
          onClick={() => setActiveTab("documents")}
        >
          Library
        </button>
        <button
          type="button"
          className={activeTab === "analytics" ? "active" : ""}
          onClick={() => setActiveTab("analytics")}
        >
          Analytics
        </button>
      </nav>

      {activeTab === "search" && (
      <section className="workspace single-panel">
        {activeTab === "search" && (
        <div className="panel">
          <h2>Upload Document</h2>
          <p className="helper-text upload-helper">
            Add a text, PDF, or Word file before asking questions about it.
          </p>
          <form onSubmit={handleUpload} className="form-stack">
            <label>
              Document file
              <input
                type="file"
                accept=".txt,.pdf,.docx,text/plain,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => setSelectedFile(event.target.files[0])}
              />
            </label>
            <button type="submit" disabled={loading || !token}>
              {loading ? "Working..." : "Upload document"}
            </button>
          </form>
        </div>
        )}

        {activeTab === "search" && (
        <div className="panel">
          <div className="mode-header">
            <h2>{mode === "search" ? "Search" : "Chat"}</h2>
            <div className="mode-toggle">
              <button
                type="button"
                className={mode === "search" ? "active" : ""}
                onClick={() => setMode("search")}
              >
                Search Mode
              </button>
              <button
                type="button"
                className={mode === "chat" ? "active" : ""}
                onClick={() => setMode("chat")}
              >
                Chat Mode
              </button>
            </div>
          </div>
          <form onSubmit={handleSearch} className="form-stack">
            <label>
              {mode === "search" ? "Query" : "Question"}
              <input
                type="text"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="How can caching improve performance?"
              />
            </label>
            <label>
              Results
              <input
                type="number"
                min="1"
                max="20"
                value={topK}
                onChange={(event) => setTopK(event.target.value)}
              />
            </label>
            <button type="submit" disabled={loading || !token}>
              {loading ? "Searching..." : mode === "search" ? "Search" : "Send"}
            </button>
          </form>
        </div>
        )}
      </section>
      )}

      {activeTab === "analytics" && (
      <>
      {analyticsLoading && <p className="loading-line">Loading analytics...</p>}
      {dashboardStats.total_uploaded_files === 0 &&
        dashboardStats.total_indexed_chunks === 0 &&
        dashboardStats.total_searches === 0 &&
        !analyticsLoading && (
          <section className="documents-section">
            <div className="panel">
              <EmptyState
                title="No analytics yet"
                message="Upload documents and run searches to populate this dashboard."
              />
            </div>
          </section>
        )}
      <section className="stats-grid analytics-grid">
        <article className="stat-card">
          <span>Files</span>
          <strong>{dashboardStats.total_uploaded_files}</strong>
          <small>Uploaded sources</small>
        </article>
        <article className="stat-card">
          <span>Chunks</span>
          <strong>{dashboardStats.total_indexed_chunks}</strong>
          <small>Searchable passages</small>
        </article>
        <article className="stat-card">
          <span>Searches</span>
          <strong>{dashboardStats.total_searches}</strong>
          <small>Saved queries</small>
        </article>
        <article className="stat-card">
          <span>Speed</span>
          <strong>{dashboardStats.average_search_time_ms} ms</strong>
          <small>Average response time</small>
        </article>
      </section>
      </>
      )}

      {activeTab === "search" && (
      <>
      {mode === "search" ? (
      <section className="content-grid">
        <div className="panel large">
          <div className="section-title">
            <h2>Generated Answer</h2>
            {searchMeta && <span>{searchMeta.executionTimeMs} ms</span>}
          </div>
          {answerSummary ? (
            <>
              <p className="answer-box">{answerSummary}</p>
              {searchMeta && (
                <div className="meta-row">
                  <span>Scanned {searchMeta.totalDocumentsScanned} documents</span>
                  <span>Cache {searchMeta.cacheHit ? "hit" : "miss"}</span>
                </div>
              )}
            </>
          ) : (
            <p className="empty">Ask a question to generate an answer summary.</p>
          )}
        </div>

        <div className="panel large">
          <div className="section-title">
            <h2>Ranked Search Results</h2>
            <span>{results.length}</span>
          </div>
          {results.length === 0 ? (
            <EmptyState
              title="No search results yet"
              message="Ask a question after uploading documents to see ranked chunks here."
            />
          ) : (
            <>
            <ResultList results={results} query={query} />
            <div className="list legacy-results-hidden">
              {results.map((result) => (
                <article key={result.id} className="result-item">
                  <div className="result-heading">
                    <h3>{result.title}</h3>
                    <strong>{result.final_score.toFixed(3)}</strong>
                  </div>
                  <p className="score-detail">
                    Final score: {result.final_score.toFixed(3)} · Semantic similarity:{" "}
                    {result.similarity_score.toFixed(3)}
                  </p>
                  <p>{previewText(result.content)}</p>
                </article>
              ))}
            </div>
            </>
          )}
        </div>
      </section>
      ) : (
        <section className="chat-section panel large">
          <div className="section-title">
            <h2>Chat</h2>
            <span>{Math.floor(chatMessages.length / 2)}</span>
          </div>

          {chatMessages.length === 0 ? (
            <p className="empty">Ask a question to start a chat with your indexed documents.</p>
          ) : (
            <div className="chat-list">
              {chatMessages.map((chatMessage) => (
                <article
                  key={chatMessage.id}
                  className={`chat-bubble ${chatMessage.role}`}
                >
                  <p>{chatMessage.content}</p>

                  {chatMessage.role === "assistant" && (
                    <>
                      <div className="meta-row chat-meta">
                        <span>{chatMessage.meta.executionTimeMs} ms</span>
                        <span>Cache {chatMessage.meta.cacheHit ? "hit" : "miss"}</span>
                      </div>

                      <details className="supporting-chunks">
                        <summary>
                          Supporting chunks ({chatMessage.supportingChunks.length})
                        </summary>
                        {chatMessage.supportingChunks.length === 0 ? (
                          <p className="empty">No supporting chunks found.</p>
                        ) : (
                          <ResultList results={chatMessage.supportingChunks} />
                        )}
                      </details>
                    </>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>
      )}

      <section className="documents-section recent-searches-section">
        <div className="panel">
          <div className="section-title">
            <h2>Recent Searches</h2>
            <span>{recentSearches.length}</span>
          </div>

              {recentSearches.length === 0 ? (
            <EmptyState
              title="No search history yet"
              message="Recent questions will appear here after your first successful search."
            />
          ) : (
            <div className="recent-search-list">
              {recentSearches.map((search) => (
                <button
                  key={search.id}
                  type="button"
                  className="recent-search-button"
                  onClick={() => handleRecentSearchClick(search.query)}
                  disabled={loading}
                >
                  <span>{search.query}</span>
                  <small>{formatDate(search.created_at)}</small>
                </button>
              ))}
            </div>
          )}
        </div>
      </section>
      </>
      )}

      {activeTab === "documents" && (
      <>
      <section className="documents-section library-section">
        <div className="panel">
          <div className="section-title">
            <h2>Uploaded Documents</h2>
            <span>{indexedChunkGroups.length}</span>
          </div>

          {indexedChunkGroups.length === 0 ? (
            <EmptyState
              title="No uploaded files"
              message="Upload a document in Ask AI to build your searchable library."
            />
          ) : (
            <div className="library-list">
              {indexedChunkGroups.map((group) => (
                <article key={group.name} className="library-item">
                  <div>
                    <h3>{group.name}</h3>
                    <p>{group.chunks.length} indexed chunk(s)</p>
                  </div>
                  <small>{formatDate(group.chunks[0].created_at)}</small>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="documents-section">
        <div className="panel">
          <div className="chunks-header">
            <div>
              <h2>Indexed Chunks</h2>
              <p className="helper-text">
                These are internal searchable chunks created from uploaded documents.
              </p>
            </div>
            <span className="count-pill">{documents.length}</span>
          </div>

          {(
            <>
              <div className="section-title compact-title">
                <span>{documents.length}</span>
              </div>
              {documents.length === 0 ? (
                <EmptyState
                  title="No indexed chunks"
                  message="Chunks are created automatically when a file upload finishes."
                />
              ) : (
                <div className="chunk-groups">
                  {indexedChunkGroups.map((group) => (
                    <article key={group.name} className="chunk-group">
                      <button
                        type="button"
                        className="chunk-group-button"
                        onClick={() =>
                          setExpandedChunkGroups((current) => ({
                            ...current,
                            [group.name]: !current[group.name],
                          }))
                        }
                      >
                        <span>{group.name}</span>
                        <strong>{group.chunks.length} chunk(s)</strong>
                      </button>

                      {expandedChunkGroups[group.name] && (
                        <div className="list chunk-list">
                          {group.chunks.map((document) => (
                            <article key={document.id} className="document-item">
                              <h3>Chunk {getChunkNumber(document)}</h3>
                              <p>{previewText(document.content)}</p>
                            </article>
                          ))}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </section>
      </>
      )}
    </main>
  );
}

function EmptyState({ title, message }) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}

function ResultList({ results, query = "" }) {
  return (
    <div className="list">
      {results.map((result) => (
        <article key={result.id} className="result-item">
          <div className="result-heading">
            <div>
              <h3>{result.title}</h3>
              <p className="result-source">
                {result.source_filename || "Manual document"} - Chunk {getChunkNumber(result)}
              </p>
            </div>
            <strong className="score-badge">
              {Math.round(result.similarity_score * 100)}% match
            </strong>
          </div>
          <p className="score-detail">
            Final score: {result.final_score.toFixed(3)} - Semantic similarity: {result.similarity_score.toFixed(3)}
          </p>
          <p>{highlightKeywords(previewText(result.content), query)}</p>
        </article>
      ))}
    </div>
  );
}

function previewText(text) {
  if (text.length <= 220) {
    return text;
  }

  return `${text.slice(0, 220)}...`;
}

function groupIndexedChunks(documents) {
  const groups = new Map();

  for (const document of documents) {
    const groupName = document.source_filename || document.title || "Untitled document";

    if (!groups.has(groupName)) {
      groups.set(groupName, []);
    }

    groups.get(groupName).push(document);
  }

  return Array.from(groups.entries())
    .map(([name, chunks]) => ({
      name,
      chunks: chunks.sort((first, second) => {
        const firstIndex = first.chunk_index ?? 0;
        const secondIndex = second.chunk_index ?? 0;
        return firstIndex - secondIndex;
      }),
    }))
    .sort((first, second) => first.name.localeCompare(second.name));
}

function getChunkNumber(document) {
  if (document.chunk_index === null || document.chunk_index === undefined) {
    return 1;
  }

  return document.chunk_index + 1;
}

function emptyDashboardStats() {
  return {
    total_uploaded_files: 0,
    total_indexed_chunks: 0,
    total_searches: 0,
    average_search_time_ms: 0,
  };
}

function formatDate(value) {
  return new Date(value).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function highlightKeywords(text, query) {
  const keywords = Array.from(
    new Set(
      query
        .toLowerCase()
        .match(/\w+/g)
        ?.filter((word) => word.length > 2) || []
    )
  );

  if (keywords.length === 0) {
    return text;
  }

  const pattern = new RegExp(`(${keywords.map(escapeRegExp).join("|")})`, "gi");

  return text.split(pattern).map((part, index) => {
    if (keywords.includes(part.toLowerCase())) {
      return <mark key={`${part}-${index}`}>{part}</mark>;
    }

    return part;
  });
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function authHeaders(token) {
  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`,
  };
}

createRoot(document.getElementById("root")).render(<App />);
