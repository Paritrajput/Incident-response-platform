import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  CgProfile,
  CgLogOut,
  CgLayoutGrid,
} from "react-icons/cg";

export default function ProfileModal({
  username,
  email,
  handleLogout,
  showProfileModal,
  closeModal,
}) {
  const modalRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!showProfileModal) return;

    const handleOutsideClick = (e) => {
      if (
        modalRef.current &&
        !modalRef.current.contains(e.target)
      ) {
        closeModal();
      }
    };

    const handleEscape = (e) => {
      if (e.key === "Escape") {
        closeModal();
      }
    };

    document.addEventListener(
      "mousedown",
      handleOutsideClick
    );
    document.addEventListener(
      "keydown",
      handleEscape
    );

    return () => {
      document.removeEventListener(
        "mousedown",
        handleOutsideClick
      );
      document.removeEventListener(
        "keydown",
        handleEscape
      );
    };
  }, [showProfileModal, closeModal]);

  if (!showProfileModal) return null;

  const menuButton =
    "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] transition hover:bg-[var(--bg-subtle)]";

  const goToDashboard = () => {
    closeModal();
    navigate("/dashboard");
  };

  const logout = async () => {
    await handleLogout();
    closeModal();
  };

  return (
    <div
      ref={modalRef}
      role="menu"
      aria-label="Profile Menu"
      className="absolute right-0 top-12 z-50 w-72 overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--bg-base)] shadow-2xl"
    >
      {/* Profile Header */}
      <div className="flex items-center gap-4 border-b border-[var(--border)] p-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--bg-subtle)] text-[var(--text-primary)]">
          <CgProfile size={28} />
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="truncate font-semibold text-[var(--text-primary)]">
            {username || "User"}
          </h3>

          <p className="truncate text-sm text-[var(--text-secondary)]">
            {email}
          </p>
        </div>
      </div>

      {/* Menu */}
      <div className="p-2">
        <button
          onClick={goToDashboard}
          className={menuButton}
        >
          <CgLayoutGrid size={20} />
          Dashboard
        </button>

        {/*
        Future Menu Items

        <button className={menuButton}>
          <CgOptions size={20}/>
          Settings
        </button>

        <button className={menuButton}>
          <CgKey size={20}/>
          API Keys
        </button>
        */}
      </div>

      {/* Footer */}
      <div className="border-t border-[var(--border)] p-2">
        <button
          onClick={logout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-red-500 transition hover:bg-red-500/10"
        >
          <CgLogOut size={20} />
          Sign Out
        </button>
      </div>
    </div>
  );
}