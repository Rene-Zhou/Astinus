import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import DiceRoller from './DiceRoller';
import type { DiceCheckRequest } from '../../api/types';

// Mock translation
vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    // Always return the key to make testing consistent
    t: (key: string) => key,
    i18n: { language: 'en' },
  }),
  initReactI18next: {
    type: '3rdParty',
    init: vi.fn(),
  },
}));

// Mock game store
const mockSpendFatePoint = vi.fn();
vi.mock('../../stores/gameStore', () => ({
  useGameStore: (selector: any) => {
    const state = { spendFatePoint: mockSpendFatePoint };
    return selector(state);
  },
}));

describe('DiceRoller', () => {
  const mockOnRoll = vi.fn();
  const mockOnCancel = vi.fn();

  const mockCheckRequest: DiceCheckRequest = {
    intention: 'Jump attack',
    dice_formula: '2d6',
    influencing_factors: { traits: ['Strong'], tags: [] },
    instructions: { cn: 'Roll', en: 'Roll it' },
  };

  it('renders nothing when not visible', () => {
    const { container } = render(
      <DiceRoller
        visible={false}
        checkRequest={null}
        fatePoints={3}
        onRoll={mockOnRoll}
        onCancel={mockOnCancel}
      />
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('renders idle state when no check request', () => {
    render(
      <DiceRoller
        visible={true}
        checkRequest={null}
        fatePoints={3}
        onRoll={mockOnRoll}
        onCancel={mockOnCancel}
      />
    );
    expect(screen.getByText('dice.panelTitle')).toBeInTheDocument();
    expect(screen.getByText('dice.waitingForCheck')).toBeInTheDocument();
  });

  it('renders check request details', () => {
    render(
      <DiceRoller
        visible={true}
        checkRequest={mockCheckRequest}
        fatePoints={3}
        onRoll={mockOnRoll}
        onCancel={mockOnCancel}
      />
    );

    expect(screen.getByText('Jump attack')).toBeInTheDocument();
    expect(screen.getByText('2d6')).toBeInTheDocument();
    expect(screen.getByText('Strong')).toBeInTheDocument();
  });

  it('handles roll and confirm flow', () => {
    render(
      <DiceRoller
        visible={true}
        checkRequest={mockCheckRequest}
        fatePoints={3}
        onRoll={mockOnRoll}
        onCancel={mockOnCancel}
      />
    );

    const rollBtn = screen.getByText(/dice.roll/i);
    fireEvent.click(rollBtn);

    // After rolling, confirm button should be enabled
    const confirmBtn = screen.getByText(/common.confirm/i);
    expect(confirmBtn).not.toBeDisabled();

    // Result should be displayed (basic check)
    expect(screen.getByText(/dice.result/i)).toBeInTheDocument();

    fireEvent.click(confirmBtn);
    expect(mockOnRoll).toHaveBeenCalled();
  });

  it('allows reroll when fate points are available', () => {
    render(
      <DiceRoller
        visible={true}
        checkRequest={mockCheckRequest}
        fatePoints={1} // Has point
        onRoll={mockOnRoll}
        onCancel={mockOnCancel}
      />
    );

    // Roll first
    fireEvent.click(screen.getByText(/dice.roll/i));

    // Reroll button should appear
    const rerollBtn = screen.getByText(/dice.reroll/i);
    expect(rerollBtn).toBeInTheDocument();

    fireEvent.click(rerollBtn);
    expect(mockSpendFatePoint).toHaveBeenCalled();
  });
});
