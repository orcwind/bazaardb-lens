import React from 'react';
import '../styles/components.css';

interface CardProps {
    type: 'monster' | 'skill' | 'item' | 'event';
    name: string;
    description: string;
    iconUrl: string;
}

export const Card: React.FC<CardProps> = ({ type, name, description, iconUrl }) => {
    const getIconClass = () => {
        switch (type) {
            case 'skill':
                return 'icon-skill';
            case 'item':
                return 'icon-item';
            case 'event':
                return 'icon-event';
            default:
                return 'icon';
        }
    };

    return (
        <div className="content-container">
            <div className="icon-container">
                <img 
                    src={iconUrl} 
                    alt={name}
                    className={getIconClass()}
                    onError={(e) => {
                        const target = e.target as HTMLImageElement;
                        target.src = '/assets/placeholder.png';
                    }}
                />
            </div>
            <div className="name">{name}</div>
            <div className="description">{description}</div>
        </div>
    );
};

export default Card; 