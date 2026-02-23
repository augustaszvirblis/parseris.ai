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

  const origin = typeof window !== "undefined" ? window.location.origin : "";
  const logoUrl = origin
    ? `${origin}${config.favicon || PARSERIS_FAVICON_DEFAULT}`
    : null;
  const siteUrl = origin ? origin : null;

  const organizationJsonLd =
    logoUrl && siteUrl
      ? {
          "@context": "https://schema.org",
          "@type": "Organization",
          name: appName,
          url: siteUrl,
          logo: logoUrl,
        }
      : null;

  const metaDescription = config.metaDescription || appName;

  return (
    <Helmet>
      <title>{title ? `${title} - ${appName}` : appName}</title>
      <meta name="description" content={metaDescription} />
      <meta property="og:description" content={metaDescription} />
      {faviconHref && (
        <link rel="icon" href={faviconHref} type="image/svg+xml" />
      )}
      {/* Logo for Google search results and social sharing */}
      {logoUrl && (
        <>
          <meta property="og:image" content={logoUrl} />
          <meta property="og:image:type" content="image/svg+xml" />
          <meta name="twitter:image" content={logoUrl} />
          {organizationJsonLd && (
            <script
              type="application/ld+json"
              dangerouslySetInnerHTML={{
                __html: JSON.stringify(organizationJsonLd),
              }}
            />
          )}
        </>
      )}
    </Helmet>
  );
}

PageTitle.propTypes = {
  title: PropTypes.string,
};

export { PageTitle };
