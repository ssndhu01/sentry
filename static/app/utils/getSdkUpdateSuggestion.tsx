import {Fragment} from 'react';
import styled from '@emotion/styled';

import ExternalLink from 'app/components/links/externalLink';
import List from 'app/components/list';
import ListItem from 'app/components/list/listItem';
import {t, tct} from 'app/locale';
import space from 'app/styles/space';
import {UpdateSdkSuggestion} from 'app/types';
import {Event} from 'app/types/event';

type Props = {
  sdk: Event['sdk'];
  suggestion: NonNullable<Event['sdkUpdates']>[0];
  shortStyle?: boolean;
  capitalized?: boolean;
};

function getSdkUpdateSuggestion({
  sdk,
  suggestion,
  shortStyle = false,
  capitalized = false,
}: Props) {
  function getUpdateSdkContent({newSdkVersion, sdkName}: UpdateSdkSuggestion) {
    if (capitalized) {
      return sdk
        ? shortStyle
          ? tct('Update to [sdk-name]@v[new-sdk-version]', {
              'sdk-name': sdkName,
              'new-sdk-version': newSdkVersion,
            })
          : tct(
              'Update your SDK from [sdk-name]@v[sdk-version] to [sdk-name]@v[new-sdk-version]',
              {
                'sdk-name': sdkName,
                'sdk-version': sdk.version,
                'new-sdk-version': newSdkVersion,
              }
            )
        : t('Update your SDK version');
    }

    return sdk
      ? shortStyle
        ? tct('update to [sdk-name]@v[new-sdk-version]', {
            'sdk-name': sdkName,
            'new-sdk-version': newSdkVersion,
          })
        : tct(
            'update your SDK from [sdk-name]@v[sdk-version] to [sdk-name]@v[new-sdk-version]',
            {
              'sdk-name': sdkName,
              'sdk-version': sdk.version,
              'new-sdk-version': newSdkVersion,
            }
          )
      : t('update your SDK version');
  }

  const getTitleData = () => {
    switch (suggestion.type) {
      case 'updateSdk':
        return {
          href: suggestion?.sdkUrl,
          content: getUpdateSdkContent(suggestion),
        };
      case 'changeSdk':
        return {
          href: suggestion?.sdkUrl,
          content: capitalized
            ? tct('Migrate to [recommended-sdk-version]', {
                'recommended-sdk-version': suggestion.newSdkName,
              })
            : tct('migrate to [recommended-sdk-version]', {
                'recommended-sdk-version': suggestion.newSdkName,
              }),
        };
      case 'enableIntegration':
        return {
          href: suggestion?.integrationUrl,
          content: capitalized
            ? tct('Enable to [recommended-integration-name]', {
                'recommended-integration-name': suggestion.integrationName,
              })
            : tct('enable to the integration [recommended-integration-name]', {
                'recommended-integration-name': suggestion.integrationName,
              }),
        };
      default:
        return null;
    }
  };

  const getTitle = () => {
    const titleData = getTitleData();

    if (!titleData) {
      return null;
    }

    const {href, content} = titleData;

    if (!href) {
      return content;
    }

    return <ExternalLink href={href}>{content}</ExternalLink>;
  };

  const title = <Fragment>{getTitle()}</Fragment>;

  if (!suggestion.enables.length) {
    return title;
  }

  const alertContent = suggestion.enables
    .map((subSuggestion, index) => {
      const subSuggestionContent = getSdkUpdateSuggestion({
        suggestion: subSuggestion,
        sdk,
        capitalized,
      });
      if (!subSuggestionContent) {
        return null;
      }
      return <ListItem key={index}>{subSuggestionContent}</ListItem>;
    })
    .filter(content => !!content);

  if (!alertContent.length) {
    return title;
  }

  return (
    <span>
      {tct('[title] so you can:', {title})}
      <StyledList symbol="bullet">{alertContent}</StyledList>
    </span>
  );
}

export default getSdkUpdateSuggestion;

const StyledList = styled(List)`
  margin-top: ${space(1)};
`;
