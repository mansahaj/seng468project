document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentUserToken = localStorage.getItem('token');
    let isLoginMode = true;

    // Elements
    const authSection = document.getElementById('auth-section');
    const dashboardSection = document.getElementById('dashboard-section');

    // Auth elements
    const tabLogin = document.getElementById('tab-login');
    const tabSignup = document.getElementById('tab-signup');
    const authForm = document.getElementById('auth-form');
    const authSubmit = document.getElementById('auth-submit');
    const authMessage = document.getElementById('auth-message');
    const logoutBtn = document.getElementById('logout-btn');

    // Dashboard elements
    const searchBtn = document.getElementById('search-btn');
    const searchQuery = document.getElementById('search-query');
    const searchResults = document.getElementById('search-results');

    const uploadBtn = document.getElementById('upload-btn');
    const pdfUpload = document.getElementById('pdf-upload');
    const uploadStatus = document.getElementById('upload-status');

    const refreshDocsBtn = document.getElementById('refresh-docs-btn');
    const documentList = document.getElementById('document-list');

    // Initialize UI
    updateUIVisibility();

    // ---------------- AUTHENTICATION ----------------

    tabLogin.addEventListener('click', () => {
        isLoginMode = true;
        tabLogin.classList.add('active');
        tabSignup.classList.remove('active');
        authSubmit.textContent = 'Login';
        authMessage.textContent = '';
    });

    tabSignup.addEventListener('click', () => {
        isLoginMode = false;
        tabSignup.classList.add('active');
        tabLogin.classList.remove('active');
        authSubmit.textContent = 'Sign Up';
        authMessage.textContent = '';
    });

    authForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        const endpoint = isLoginMode ? '/auth/login' : '/auth/signup';

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            const data = await response.json();

            if (response.ok) {
                if (isLoginMode) {
                    currentUserToken = data.token;
                    localStorage.setItem('token', currentUserToken);
                    updateUIVisibility();
                    fetchDocuments();
                } else {
                    authMessage.textContent = 'Signup successful! Please login.';
                    authMessage.style.color = 'green';
                    tabLogin.click();
                }
            } else {
                authMessage.textContent = data.detail || data.error || 'Authentication failed';
                authMessage.style.color = 'red';
            }
        } catch (error) {
            authMessage.textContent = 'Network error occurred.';
            authMessage.style.color = 'red';
        }
    });

    logoutBtn.addEventListener('click', () => {
        currentUserToken = null;
        localStorage.removeItem('token');
        updateUIVisibility();
    });

    // ---------------- DASHBOARD FUNC ----------------

    function updateUIVisibility() {
        if (currentUserToken) {
            authSection.style.display = 'none';
            dashboardSection.style.display = 'block';
            fetchDocuments();
        } else {
            authSection.style.display = 'block';
            dashboardSection.style.display = 'none';
        }
    }

    // --- Search ---
    searchBtn.addEventListener('click', async () => {
        const query = searchQuery.value.trim();
        if (!query) return;

        searchResults.innerHTML = '<p>Searching...</p>';
        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`, {
                headers: { 'Authorization': `Bearer ${currentUserToken}` }
            });

            if (!response.ok) throw new Error('Search failed');

            const results = await response.json();
            displaySearchResults(results);
        } catch (error) {
            searchResults.innerHTML = '<p style="color:red">Error performing search.</p>';
        }
    });

    function displaySearchResults(results) {
        if (!results.length) {
            searchResults.innerHTML = '<p>No results found.</p>';
            return;
        }

        searchResults.innerHTML = results.map(result => `
            <div class="result-item">
                <div class="result-meta">
                    <span>Source: ${result.filename}</span>
                    <span class="score">Score: ${result.score.toFixed(3)}</span>
                </div>
                <p>${result.text}</p>
            </div>
        `).join('');
    }

    // --- Documents ---
    uploadBtn.addEventListener('click', async () => {
        const file = pdfUpload.files[0];
        if (!file) {
            uploadStatus.textContent = 'Please select a PDF file.';
            uploadStatus.style.color = 'red';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        uploadStatus.textContent = 'Uploading...';
        uploadStatus.style.color = '#4a90e2';

        try {
            const response = await fetch('/documents', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${currentUserToken}` },
                body: formData
            });

            if (response.ok) {
                uploadStatus.textContent = 'Upload successful!';
                uploadStatus.style.color = 'green';
                pdfUpload.value = ''; // clear input
                fetchDocuments();
            } else {
                throw new Error('Upload failed');
            }
        } catch (error) {
            uploadStatus.textContent = 'Error uploading file.';
            uploadStatus.style.color = 'red';
        }
    });

    refreshDocsBtn.addEventListener('click', fetchDocuments);

    async function fetchDocuments() {
        try {
            const response = await fetch('/documents', {
                headers: { 'Authorization': `Bearer ${currentUserToken}` }
            });

            if (response.ok) {
                const docs = await response.json();
                displayDocuments(docs);
            }
        } catch (error) {
            console.error('Failed to fetch documents', error);
        }
    }

    function displayDocuments(docs) {
        if (!docs.length) {
            documentList.innerHTML = '<li>No documents uploaded yet.</li>';
            return;
        }

        documentList.innerHTML = docs.map(doc => `
            <li class="doc-item">
                <div class="doc-info">
                    <span class="doc-name">${doc.filename}</span>
                    <span class="doc-status">Status: ${doc.status} | Uploaded: ${new Date(doc.upload_date).toLocaleString()}</span>
                </div>
                <button class="btn small danger delete-doc-btn" data-id="${doc.document_id}">Delete</button>
            </li>
        `).join('');

        // Attach event listeners to delete buttons
        document.querySelectorAll('.delete-doc-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const docId = e.target.getAttribute('data-id');
                await deleteDocument(docId);
            });
        });
    }

    async function deleteDocument(docId) {
        if (!confirm('Are you sure you want to delete this document?')) return;

        try {
            const response = await fetch(`/documents/${docId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${currentUserToken}` }
            });

            if (response.ok) {
                fetchDocuments();
            } else {
                alert('Failed to delete document');
            }
        } catch (error) {
            console.error('Error deleting document', error);
        }
    }
});
