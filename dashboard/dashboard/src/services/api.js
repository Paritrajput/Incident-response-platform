const API_BASE =
    import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(
    endpoint,
    options = {}
) {
    const response = await fetch(
        `${API_BASE}${endpoint}`,
        {
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                ...(options.headers || {}),
            },
            ...options,
        }
    );

    let data = {};

    try {
        data = await response.json();
    } catch (_) {}

    if (!response.ok) {
        throw new Error(
            data.detail ||
            data.message ||
            "Something went wrong."
        );
    }

    return data;
}

const api = {

    get(endpoint) {
        return request(endpoint);
    },

    post(endpoint, body) {
        return request(endpoint, {
            method: "POST",
            body: JSON.stringify(body),
        });
    },

    put(endpoint, body) {
        return request(endpoint, {
            method: "PUT",
            body: JSON.stringify(body),
        });
    },

    delete(endpoint) {
        return request(endpoint, {
            method: "DELETE",
        });
    },

};

export const applicationsApi = {
    list: () => api.get("/applications/"),
    create: (body) => api.post("/applications/", body),
    update: (applicationId, body) => api.put(`/applications/${applicationId}`, body),
    remove: (applicationId) => api.delete(`/applications/${applicationId}`),
    integrations: (applicationId) => api.get(`/applications/${applicationId}/integrations`),
    connectIntegration: (applicationId, type, body) =>
        api.post(`/applications/${applicationId}/integrations/${type}`, body),
    disconnectIntegration: (applicationId, type) =>
        api.delete(`/applications/${applicationId}/integrations/${type}`),
    incidents: (applicationId) => api.get(`/applications/${applicationId}/incidents`),
    deploys: (applicationId) => api.get(`/applications/${applicationId}/deploys`),
};

export default api;
