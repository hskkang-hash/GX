/**
 * UX-15 **단축키 안내** — 안 보이는 단축키는 없는 단축키다.
 *
 * ★ 이 표는 「무엇을 눌렀나」가 아니라 **「무엇이 일어나나」**를 적는다. 단축키를
 *   외운 사람은 이 상자를 안 열고, 처음 온 사람은 이것 말고 알 길이 없다.
 * ★ 단추 라벨과 **같은 낱말**을 쓴다(접수하기 · 조치 시작 · 종결하기). 안내와 단추가
 *   다른 말을 쓰면 사람이 둘을 다른 일로 읽는다.
 */
import { Card, Typography } from 'antd';
import type { CSSProperties } from 'react';

const { Text } = Typography;

const KEY_BOX: CSSProperties = {
  display: 'inline-block',
  minWidth: 30,
  padding: '1px 8px',
  marginRight: 10,
  border: '1px solid #d9d9d9',
  borderRadius: 4,
  background: '#fafafa',
  fontFamily: 'monospace',
  textAlign: 'center',
};

const ROWS: Array<[string, string]> = [
  ['J', '아래로'],
  ['K', '위로'],
  ['Enter', '상세 열기'],
  ['1', '접수하기'],
  ['2', '조치 시작'],
  ['3', '종결하기'],
  ['M', '소리 켜기 / 소리 끄기'],
];

interface Props {
  /** 숫자 키가 지금 누구에게 드는지 한 줄로 적는다. 없으면 그 줄을 안 그린다. */
  targetNote?: string;
}

export default function ShortcutHelp({ targetNote }: Props) {
  return (
    <Card size="small" title="단축키 안내">
      <div>
        {ROWS.map(([key, what]) => (
          <div key={key} style={{ marginBottom: 4 }}>
            <span style={KEY_BOX}>{key}</span>
            <Text>{what}</Text>
          </div>
        ))}
      </div>
      {targetNote ? (
        <div style={{ marginTop: 8 }}>
          <Text type="secondary">{targetNote}</Text>
        </div>
      ) : null}
      <div style={{ marginTop: 4 }}>
        <Text type="secondary">
          소리는 심각에서만 납니다. 묶인 카드는 한 번만 납니다. 글자를 쓰는 칸에
          있을 때는 단축키가 들지 않습니다.
        </Text>
      </div>
    </Card>
  );
}
