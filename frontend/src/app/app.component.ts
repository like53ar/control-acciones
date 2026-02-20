import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PortfolioService, PortfolioResponse } from './portfolio.service';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './app.component.html'
})
export class AppComponent implements OnInit, OnDestroy {
    title = 'Portafolio Zen';
    portfolioData: PortfolioResponse | null = null;
    loading = true;

    // Formulario de Inversión
    newItem = {
        symbol: '',
        company: '',
        quantity: null as number | null,
        buy_price: null as number | null,
        buy_date: new Date().toISOString().split('T')[0] // Default to today
    };
    submitting = false;
    loadingCompany = false;

    private symbolSubject = new Subject<string>();
    private symbolSubscription!: Subscription;

    constructor(private portfolioService: PortfolioService) { }

    ngOnInit() {
        this.fetchData();

        // Listener para buscar el nombre de la empresa sin saturar la API
        this.symbolSubscription = this.symbolSubject.pipe(
            debounceTime(500),
            distinctUntilChanged()
        ).subscribe(symbol => {
            if (symbol && symbol.trim().length > 0) {
                this.loadingCompany = true;
                this.portfolioService.getQuote(symbol).subscribe({
                    next: (res) => {
                        this.newItem.company = res.company;
                        this.loadingCompany = false;
                    },
                    error: () => {
                        this.newItem.company = '';
                        this.loadingCompany = false;
                    }
                });
            } else {
                this.newItem.company = '';
            }
        });
    }

    ngOnDestroy() {
        if (this.symbolSubscription) {
            this.symbolSubscription.unsubscribe();
        }
    }

    onSymbolChange(value: string) {
        this.symbolSubject.next(value);
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
            alert('Por favor, completa todos los campos requeridos para añadir tu inversión.');
            return;
        }

        this.submitting = true;

        // Formatear payload para enviarlo al backend
        const payload: any = {
            symbol: this.newItem.symbol,
            quantity: this.newItem.quantity,
            buy_price: this.newItem.buy_price
        };

        if (this.newItem.company) payload.company = this.newItem.company;
        if (this.newItem.buy_date) payload.buy_date = this.newItem.buy_date;

        this.portfolioService.addPortfolioItem(payload).subscribe({
            next: () => {
                this.newItem = {
                    symbol: '',
                    company: '',
                    quantity: null,
                    buy_price: null,
                    buy_date: new Date().toISOString().split('T')[0]
                };
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

    // Modal de Confirmación
    showDeleteModal = false;
    itemToDelete: any = null;
    isDeleting = false;

    confirmDelete(item: any) {
        this.itemToDelete = item;
        this.showDeleteModal = true;
    }

    cancelDelete() {
        this.showDeleteModal = false;
        this.itemToDelete = null;
    }

    executeDelete() {
        if (!this.itemToDelete) return;

        this.isDeleting = true;
        this.portfolioService.deletePortfolioItem(this.itemToDelete.id).subscribe({
            next: () => {
                // Refresco "silencioso" para no hacer titilar toda la página
                this.portfolioService.getPortfolio().subscribe(data => {
                    this.portfolioData = data;
                    this.isDeleting = false;
                    this.showDeleteModal = false;
                    this.itemToDelete = null;
                });
            },
            error: (err) => {
                console.error('Error al eliminar posición', err);
                this.isDeleting = false;
                this.showDeleteModal = false;
                this.itemToDelete = null;
            }
        });
    }

    // Modal de Venta
    showSellModal = false;
    itemToSell: any = null;
    isSelling = false;
    sellPrice: number | null = null;
    sellDate: string = new Date().toISOString().split('T')[0];

    confirmSell(item: any) {
        this.itemToSell = item;
        this.sellPrice = item.CurrentPrice;
        this.sellDate = new Date().toISOString().split('T')[0];
        this.showSellModal = true;
    }

    cancelSell() {
        this.showSellModal = false;
        this.itemToSell = null;
    }

    executeSell() {
        if (!this.itemToSell || !this.sellPrice || !this.sellDate) return;

        this.isSelling = true;
        this.portfolioService.sellPortfolioItem(this.itemToSell.id, {
            sell_price: this.sellPrice,
            sell_date: this.sellDate
        }).subscribe({
            next: () => {
                this.portfolioService.getPortfolio().subscribe(data => {
                    this.portfolioData = data;
                    this.isSelling = false;
                    this.showSellModal = false;
                    this.itemToSell = null;
                });
            },
            error: (err) => {
                console.error('Error al vender posición', err);
                this.isSelling = false;
            }
        });
    }
}
