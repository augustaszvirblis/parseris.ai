import { Typography } from "antd";
import PropTypes from "prop-types";

import "./GenericLoader.css";

/**
 * Inline P logo (same as parseris-favicon.svg) so it renders with first paint, no load lag.
 * @param {Object} props
 * @param {string} [props.className] - Optional CSS class name.
 * @return {JSX.Element}
 */
function ParserisLogoIcon({ className }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      aria-hidden
    >
      <rect width="32" height="32" rx="6" fill="#252F3E" />
      <path
        d="M10 8h9c3.3 0 6 2.7 6 6s-2.7 6-6 6h-5v6H10V8zm2 2v8h7c2.2 0 4-1.8 4-4s-1.8-4-4-4h-7z"
        fill="#FF9900"
      />
    </svg>
  );
}

ParserisLogoIcon.propTypes = {
  className: PropTypes.string,
};

function GenericLoader() {
  return (
    <div className="center">
      <div className="spinner-box">
        <ParserisLogoIcon className="generic-loader-logo" />
        <div className="pulse-container">
          <div className="pulse-bubble pulse-bubble-1"></div>
          <div className="pulse-bubble pulse-bubble-2"></div>
          <div className="pulse-bubble pulse-bubble-3"></div>
          <div className="pulse-bubble pulse-bubble-4"></div>
        </div>
        <Typography>
          Please wait before we prepare your session. <br></br>This might take a
          minute.
        </Typography>
      </div>
    </div>
  );
}

export { GenericLoader };
