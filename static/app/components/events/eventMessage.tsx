import * as React from 'react';
import styled from '@emotion/styled';

import ErrorLevel from 'app/components/events/errorLevel';
import overflowEllipsis from 'app/styles/overflowEllipsis';
import space from 'app/styles/space';
import {Level} from 'app/types';

type Props = {
  level?: Level;
  levelIndicatorSize?: string;
  message?: React.ReactNode;
  annotations?: React.ReactNode;
  className?: string;
  hasGuideAnchor?: boolean;
};

const BaseEventMessage = ({
  className,
  level,
  levelIndicatorSize,
  message,
  annotations,
}: Props) => (
  <div className={className}>
    {level && (
      <StyledErrorLevel size={levelIndicatorSize} level={level}>
        {level}
      </StyledErrorLevel>
    )}

    {message && <Message>{message}</Message>}

    {annotations}
  </div>
);

const EventMessage = styled(BaseEventMessage)`
  display: flex;
  align-items: center;
  position: relative;
  line-height: 1.2;
  overflow: hidden;
`;

const StyledErrorLevel = styled(ErrorLevel)`
  margin-right: ${space(1)};
`;

const Message = styled('span')`
  ${overflowEllipsis}
  width: auto;
  max-height: 38px;
`;

export default EventMessage;
