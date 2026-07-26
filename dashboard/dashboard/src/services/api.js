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

export default api;