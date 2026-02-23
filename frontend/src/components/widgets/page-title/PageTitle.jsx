import { Helmet } from "react-helmet-async";
import PropTypes from "prop-types";

import config from "../../../config";

/** Favicon path for Parseris.ai (browser tab logo). Use config.favicon if set, else default asset. */
const PARSERIS_FAVICON_DEFAULT = "/parseris-favicon.svg";

function PageTitle({ title }) {
  const appName = config.appName || "Unstract";
  const isParseris = appName === "Parseris.ai";
  const faviconHref =
    isParseris &&
    (config.favicon && config.favicon !== "/favicon.ico"
      ? config.favicon
      : PARSERIS_FAVICON_DEFAULT);
  return (
    <Helmet>
      <title>{title ? `${title} - ${appName}` : appName}</title>
      {faviconHref && (
        <link rel="icon" href={faviconHref} type="image/svg+xml" />
      )}
    </Helmet>
  );
}

PageTitle.propTypes = {
  title: PropTypes.string,
};

export { PageTitle };
