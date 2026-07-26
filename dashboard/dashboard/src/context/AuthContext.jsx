import {
    createContext,
    useContext,
    useEffect,
    useState,
} from "react";

import api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // --------------------------------------------------
    // Check existing login session
    // --------------------------------------------------
    const refreshUser = async () => {
        try {
            const data = await api.get("/auth/me");
            setUser(data.user);
        } catch (err) {
            setUser(null);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        refreshUser();
    }, []);

    // --------------------------------------------------
    // Login
    // --------------------------------------------------
    const login = async (email, password) => {
        const data = await api.post("/auth/login", {
            email,
            password,
        });

        setUser(data.user);

        return data;
    };
useEffect(() => {
    console.log("Current user:", user);
}, [user]);
    // --------------------------------------------------
    // Signup
    // --------------------------------------------------
    const signup = async (
        username,
        email,
        password
    ) => {
        return api.post("/auth/signup", {
            username,
            email,
            password,
        });
    };

    // --------------------------------------------------
    // Logout
    // --------------------------------------------------
    const logout = async () => {
        try {
            await api.post("/auth/logout");
        } finally {
            setUser(null);
        }
    };

    // --------------------------------------------------
    // Context Value
    // --------------------------------------------------
    const value = {
        user,
        loading,
        login,
        signup,
        logout,
        refreshUser,
        isAuthenticated: !!user,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);

    if (!context) {
        throw new Error(
            "useAuth must be used inside AuthProvider."
        );
    }

    return context;
}