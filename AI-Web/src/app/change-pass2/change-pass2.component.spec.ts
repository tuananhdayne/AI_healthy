import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChangePass2Component } from './change-pass2.component';

describe('ChangePass2Component', () => {
  let component: ChangePass2Component;
  let fixture: ComponentFixture<ChangePass2Component>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ ChangePass2Component ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ChangePass2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
