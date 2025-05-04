import React from 'react';
import Card from './Card';
import '../styles/components.css';

interface CardData {
    type: 'monster' | 'skill' | 'item' | 'event';
    name: string;
    description: string;
    iconUrl: string;
}

interface CardGridProps {
    cards: CardData[];
}

export const CardGrid: React.FC<CardGridProps> = ({ cards }) => {
    return (
        <div className="grid-container">
            {cards.map((card, index) => (
                <Card
                    key={`${card.type}-${index}`}
                    type={card.type}
                    name={card.name}
                    description={card.description}
                    iconUrl={card.iconUrl}
                />
            ))}
        </div>
    );
};

export default CardGrid; 