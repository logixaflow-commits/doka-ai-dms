window.FetchHelper = {
  isLoading: false,
  loadingMessage: '',
  fetchWithLoading(url, options = {}, onSuccess, onError, loadingMessage = 'Loading...') {
    this.isLoading = true;
    this.loadingMessage = loadingMessage;
    return fetch(url, options)
      .then((response) => response.json())
      .then((data) => {
        this.isLoading = false;
        this.loadingMessage = '';
        if (onSuccess) onSuccess(data);
        return data;
      })
      .catch((error) => {
        this.isLoading = false;
        this.loadingMessage = '';
        if (onError) onError(error);
        throw error;
      });
  }
};
