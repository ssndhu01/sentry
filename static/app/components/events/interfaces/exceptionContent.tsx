import * as React from 'react';
import styled from '@emotion/styled';

import ExceptionMechanism from 'app/components/events/interfaces/exceptionMechanism';
import Annotated from 'app/components/events/meta/annotated';
import space from 'app/styles/space';
import {ExceptionType} from 'app/types';
import {Event} from 'app/types/event';
import {STACK_TYPE} from 'app/types/stacktrace';

import ExceptionStacktraceContent from './exceptionStacktraceContent';
import ExceptionTitle from './exceptionTitle';

type ExceptionStacktraceContentProps = React.ComponentProps<
  typeof ExceptionStacktraceContent
>;

type Props = {
  event: Event;
  type: STACK_TYPE;
  platform: ExceptionStacktraceContentProps['platform'];
  stackView?: ExceptionStacktraceContentProps['stackView'];
  newestFirst?: boolean;
} & Pick<ExceptionType, 'values'> &
  Pick<
    React.ComponentProps<typeof ExceptionStacktraceContent>,
    'groupingCurrentLevel' | 'hasHierarchicalGrouping'
  >;

const ExceptionContent = ({
  newestFirst,
  event,
  stackView,
  groupingCurrentLevel,
  hasHierarchicalGrouping,
  platform,
  values,
  type,
}: Props) => {
  if (!values) {
    return null;
  }

  const children = values.map((exc, excIdx) => (
    <div key={excIdx} className="exception">
      <ExceptionTitle type={exc.type} exceptionModule={exc?.module} />
      <Annotated object={exc} objectKey="value" required>
        {value => <StyledPre className="exc-message">{value}</StyledPre>}
      </Annotated>
      {exc.mechanism && <ExceptionMechanism data={exc.mechanism} />}
      <ExceptionStacktraceContent
        data={
          type === STACK_TYPE.ORIGINAL
            ? exc.stacktrace
            : exc.rawStacktrace || exc.stacktrace
        }
        stackView={stackView}
        stacktrace={exc.stacktrace}
        expandFirstFrame={excIdx === values.length - 1}
        platform={platform}
        newestFirst={newestFirst}
        event={event}
        chainedException={values.length > 1}
        hasHierarchicalGrouping={hasHierarchicalGrouping}
        groupingCurrentLevel={groupingCurrentLevel}
      />
    </div>
  ));

  if (newestFirst) {
    children.reverse();
  }

  return <div>{children}</div>;
};

export default ExceptionContent;

const StyledPre = styled('pre')`
  margin-bottom: ${space(1)};
  margin-top: 0;
`;
