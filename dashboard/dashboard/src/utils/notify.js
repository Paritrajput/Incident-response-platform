import toast from "react-hot-toast";

export const notify = {

  success(message) {
    toast.success(message);
  },

  error(message) {
    toast.error(message);
  },

  loading(message = "Loading...") {
    return toast.loading(message);
  },

  dismiss(id) {
    toast.dismiss(id);
  },

  promise(promise, messages) {
    return toast.promise(promise, {
      loading: messages.loading,
      success: messages.success,
      error: messages.error,
    });
  },
};