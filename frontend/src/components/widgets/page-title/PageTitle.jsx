import { Helmet } from "react-helmet-async";
import PropTypes from "prop-types";

import config from "../../../config";

/** Minimal transparent favicon (no Unstract logo) when using Parseris branding. */
const PARSERIS_FAVICON =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1 1'%3E%3C/svg%3E";

function PageTitle({ title }) {
  const appName = config.appName || "Unstract";
  const isParseris = appName === "Parseris.ai";
  return (
    <Helmet>
      <title>{title ? `${title} - ${appName}` : appName}</title>
      {isParseris && (
        <link rel="icon" href={PARSERIS_FAVICON} type="image/svg+xml" />
      )}
    </Helmet>
  );
}

PageTitle.propTypes = {
  title: PropTypes.string,
};

export { PageTitle };
