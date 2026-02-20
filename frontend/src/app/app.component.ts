import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService, PortfolioResponse } from './portfolio.service';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './app.component.html'
})
export class AppComponent implements OnInit {
    title = 'Portafolio Zen';
    portfolioData: PortfolioResponse | null = null;
    loading = true;

    // Formulario de Inversión
    newItem = {
        symbol: '',
        quantity: null as number | null,
        buy_price: null as number | null
    };
    submitting = false;

    constructor(private portfolioService: PortfolioService) { }

    ngOnInit() {
        this.fetchData();
    }

    fetchData() {
        this.loading = true;
        this.portfolioService.getPortfolio().subscribe({
            next: (data) => {
                this.portfolioData = data;
                this.loading = false;
            },
            error: (err) => {
                console.error('Error al obtener portafolio', err);
                this.loading = false;
            }
        });
    }

    addItem() {
        if (!this.newItem.symbol || !this.newItem.quantity || !this.newItem.buy_price) {
            alert('Por favor, completa todos los campos para añadir tu inversión.');
            return;
        }

        this.submitting = true;
        this.portfolioService.addPortfolioItem({
            symbol: this.newItem.symbol,
            quantity: this.newItem.quantity,
            buy_price: this.newItem.buy_price
        }).subscribe({
            next: () => {
                this.newItem = { symbol: '', quantity: null, buy_price: null };
                this.submitting = false;
                this.fetchData();
            },
            error: (err) => {
                console.error('Error al añadir posición', err);
                alert('Hubo un error al conectarse con el servidor para guardar la posición.');
                this.submitting = false;
            }
        });
    }

    deleteItem(id: number) {
        if (confirm('¿Deseas cerrar esta posición de tu portafolio? La acción es irreversible.')) {
            this.loading = true;
            this.portfolioService.deletePortfolioItem(id).subscribe({
                next: () => {
                    this.fetchData();
                },
                error: (err) => {
                    console.error('Error al eliminar posición', err);
                    alert('No se pudo eliminar la posición.');
                    this.loading = false;
                }
            });
        }
    }
}
