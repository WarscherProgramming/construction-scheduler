import { Component } from "react";

import Button from "./Button";

/**
 * Catches render errors in its subtree and shows a recoverable fallback
 * instead of letting the whole app unmount. "Try again" clears the error and
 * re-renders the children.
 */
class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught a render error", error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      const {
        title = "Something went wrong",
        description = "This section failed to display. Your data is safe — try loading it again.",
      } = this.props;

      return (
        <div className="error-boundary" role="alert">
          <strong className="error-boundary__title">{title}</strong>
          <p className="error-boundary__description">{description}</p>
          <Button onClick={this.handleRetry}>Try again</Button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
