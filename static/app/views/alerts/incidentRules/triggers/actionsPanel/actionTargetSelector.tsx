import * as React from 'react';

import SelectControl from 'app/components/forms/selectControl';
import TeamSelector from 'app/components/forms/teamSelector';
import SelectMembers from 'app/components/selectMembers';
import {Organization, Project, SelectValue} from 'app/types';
import {
  Action,
  ActionType,
  MetricActionTemplate,
  TargetType,
} from 'app/views/alerts/incidentRules/types';
import Input from 'app/views/settings/components/forms/controls/input';

const getPlaceholderForType = (type: ActionType) => {
  switch (type) {
    case ActionType.SLACK:
      return '@username or #channel';
    case ActionType.MSTEAMS:
      // no prefixes for msteams
      return 'username or channel';
    case ActionType.PAGERDUTY:
      return 'service';
    default:
      throw Error('Not implemented');
  }
};

type Props = {
  action: Action;
  availableAction?: MetricActionTemplate;
  disabled: boolean;
  loading: boolean;
  organization: Organization;
  project?: Project;
  onChange: (value: string) => void;
};

export default function ActionTargetSelector(props: Props) {
  const {action, availableAction, disabled, loading, onChange, organization, project} =
    props;

  const handleChangeTargetIdentifier = (value: SelectValue<string>) => {
    onChange(value.value);
  };

  const handleChangeSpecificTargetIdentifier = (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    onChange(e.target.value);
  };

  switch (action.targetType) {
    case TargetType.TEAM:
    case TargetType.USER:
      const isTeam = action.targetType === TargetType.TEAM;

      return isTeam ? (
        <TeamSelector
          disabled={disabled}
          key="team"
          project={project}
          value={action.targetIdentifier}
          onChange={handleChangeTargetIdentifier}
          useId
        />
      ) : (
        <SelectMembers
          disabled={disabled}
          key="member"
          project={project}
          organization={organization}
          value={action.targetIdentifier}
          onChange={handleChangeTargetIdentifier}
        />
      );

    case TargetType.SPECIFIC:
      return availableAction?.options ? (
        <SelectControl
          isDisabled={disabled || loading}
          value={action.targetIdentifier}
          options={availableAction.options}
          onChange={handleChangeTargetIdentifier}
        />
      ) : (
        <Input
          type="text"
          autoComplete="off"
          disabled={disabled}
          key={action.type}
          value={action.targetIdentifier || ''}
          onChange={handleChangeSpecificTargetIdentifier}
          placeholder={getPlaceholderForType(action.type)}
        />
      );

    default:
      return null;
  }
}
